#include "ns3/core-module.h"
#include "ns3/network-module.h"

#include <cmath>
#include <fstream>
#include <iomanip>
#include <map>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("LoraDriftGt");

static inline double
PpmToEps(double ppm)
{
  return ppm * 1e-6;
}

static inline Time
GlobalToLocal(Time global, double eps)
{
  return Seconds(global.GetSeconds() * (1.0 + eps));
}

static inline Time
LocalToGlobal(Time local, double eps)
{
  return Seconds(local.GetSeconds() / (1.0 + eps));
}

class TreeMeshMetricsReady
{
public:
  TreeMeshMetricsReady(double intervalS,
                       double simTimeS,
                       double hopDelayS,
                       double relayProcDelayS,
                       double srcPpm,
                       double relayPpm,
                       double sinkPpm,
                       const std::string& gtModel,
                       double fixedGtMs,
                       double baseGtMs,
                       double gainK,
                       double minGtMs,
                       double maxGtMs,
                       uint32_t seed,
                       uint32_t run,
                       const std::string& csvPath)
      : m_intervalLocal(Seconds(intervalS)),
        m_simTime(Seconds(simTimeS)),
        m_hopDelay(Seconds(hopDelayS)),
        m_relayProcDelayLocal(Seconds(relayProcDelayS)),
        m_gtModel(gtModel),
        m_fixedGt(MilliSeconds(fixedGtMs)),
        m_baseGt(MilliSeconds(baseGtMs)),
        m_gainK(gainK),
        m_minGt(MilliSeconds(minGtMs)),
        m_maxGt(MilliSeconds(maxGtMs)),
        m_srcEps(PpmToEps(srcPpm)),
        m_relayEps(PpmToEps(relayPpm)),
        m_sinkEps(PpmToEps(sinkPpm)),
        m_srcPpm(srcPpm),
        m_relayPpm(relayPpm),
        m_sinkPpm(sinkPpm),
        m_fixedGtMs(fixedGtMs),
        m_baseGtMs(baseGtMs),
        m_minGtMs(minGtMs),
        m_maxGtMs(maxGtMs),
        m_seed(seed),
        m_run(run),
        m_csvPath(csvPath)
  {
    m_sink = 0;
    m_relays = {1, 2};
    m_sources = {3, 4, 5};

    // Parent-child tree
    m_parent[3] = 1; // Source1 -> Relay1
    m_parent[4] = 1; // Source2 -> Relay1
    m_parent[5] = 2; // Source3 -> Relay2
    m_parent[1] = 0; // Relay1 -> Sink
    m_parent[2] = 0; // Relay2 -> Sink
  }

  void Run()
  {
    NS_LOG_INFO("Phase 1 Step 7: Metrics/logging-ready 6-node tree-based mesh");
    NS_LOG_INFO("gtModel=" << m_gtModel
                 << " srcPpm=" << m_srcPpm
                 << " relayPpm=" << m_relayPpm
                 << " sinkPpm=" << m_sinkPpm
                 << " seed=" << m_seed
                 << " run=" << m_run);

    for (auto src : m_sources)
    {
      m_sourceSeq[src] = 0;
      ScheduleSourceStart(src, Seconds(1.0));
    }

    Simulator::Stop(m_simTime);
    Simulator::Run();
    Simulator::Destroy();

    SaveCsv();
    PrintSummary();
  }

private:
  struct PacketInfo
  {
    uint32_t sourceId;
    uint32_t seq;
    Time createdAtGlobal;
  };

  struct StreamWindow
  {
    bool valid{false};
    Time expectedLocal{Seconds(0)};
    Time lastAbsErr{Seconds(0)};
  };

  double GetNodeEps(uint32_t nodeId) const
  {
    if (nodeId == m_sink)
    {
      return m_sinkEps;
    }
    if (nodeId == 1 || nodeId == 2)
    {
      return m_relayEps;
    }
    return m_srcEps;
  }

  void ScheduleSourceStart(uint32_t src, Time firstGlobal)
  {
    if (firstGlobal < m_simTime)
    {
      Simulator::Schedule(firstGlobal, &TreeMeshMetricsReady::SourceSend, this, src);
    }
  }

  void SourceSend(uint32_t src)
  {
    PacketInfo p;
    p.sourceId = src;
    p.seq = m_sourceSeq[src]++;
    p.createdAtGlobal = Simulator::Now();

    m_txTotal++;

    double eps = GetNodeEps(src);
    Time nowGlobal = Simulator::Now();
    Time nowLocal = GlobalToLocal(nowGlobal, eps);

    NS_LOG_INFO("TX Source" << src
                 << " seq=" << p.seq
                 << " global=" << nowGlobal.GetSeconds() << "s"
                 << " local=" << nowLocal.GetSeconds() << "s"
                 << " -> Relay" << m_parent[src]);

    uint32_t relay = m_parent[src];
    Simulator::Schedule(m_hopDelay,
                        &TreeMeshMetricsReady::ReceiveAtRelay,
                        this,
                        relay,
                        p);

    Time nextLocal = nowLocal + m_intervalLocal;
    Time nextGlobal = LocalToGlobal(nextLocal, eps);

    if (nextGlobal < m_simTime)
    {
      Time delay = nextGlobal - Simulator::Now();
      if (delay.IsNegative())
      {
        delay = NanoSeconds(1);
      }
      Simulator::Schedule(delay, &TreeMeshMetricsReady::SourceSend, this, src);
    }
  }

  Time ComputeCurrentGt(StreamWindow& w) const
  {
    if (m_gtModel == "fixed")
    {
      return m_fixedGt;
    }

    double gtSec = m_baseGt.GetSeconds() + m_gainK * w.lastAbsErr.GetSeconds();

    if (gtSec < m_minGt.GetSeconds())
    {
      gtSec = m_minGt.GetSeconds();
    }
    if (gtSec > m_maxGt.GetSeconds())
    {
      gtSec = m_maxGt.GetSeconds();
    }

    return Seconds(gtSec);
  }

  bool CheckWindow(StreamWindow& w, Time arrivalLocal, Time& errOut, Time& gtUsedOut)
  {
    if (!w.valid)
    {
      w.valid = true;
      w.expectedLocal = arrivalLocal;
      errOut = Seconds(0);
      gtUsedOut = (m_gtModel == "fixed") ? m_fixedGt : m_baseGt;
      w.lastAbsErr = Seconds(0);
      w.expectedLocal += m_intervalLocal;
      return true;
    }

    gtUsedOut = ComputeCurrentGt(w);

    errOut = arrivalLocal - w.expectedLocal;
    bool ok = std::fabs(errOut.GetSeconds()) <= gtUsedOut.GetSeconds();

    w.lastAbsErr = Seconds(std::fabs(errOut.GetSeconds()));
    w.expectedLocal += m_intervalLocal;
    return ok;
  }

  void ReceiveAtRelay(uint32_t relay, PacketInfo p)
  {
    m_relayRxTotal++;

    double eps = GetNodeEps(relay);
    Time nowGlobal = Simulator::Now();
    Time nowLocal = GlobalToLocal(nowGlobal, eps);

    Time err = Seconds(0);
    Time gtUsed = Seconds(0);

    StreamWindow& w = m_expectedAtRelay[relay][p.sourceId];
    bool ok = CheckWindow(w, nowLocal, err, gtUsed);

    if (ok)
    {
      m_relayRxOk++;

      NS_LOG_INFO("RX_OK Relay" << relay
                   << " src=" << p.sourceId
                   << " seq=" << p.seq
                   << " err_ms=" << err.GetMilliSeconds()
                   << " gt_used_ms=" << gtUsed.GetMilliSeconds());

      Time fwdLocal = nowLocal + m_relayProcDelayLocal;
      Time fwdGlobal = LocalToGlobal(fwdLocal, eps);
      Time delay = fwdGlobal - Simulator::Now();
      if (delay.IsNegative())
      {
        delay = NanoSeconds(1);
      }

      Simulator::Schedule(delay,
                          &TreeMeshMetricsReady::ForwardFromRelay,
                          this,
                          relay,
                          p);
    }
    else
    {
      m_relayViol++;

      NS_LOG_INFO("VIOL Relay" << relay
                   << " src=" << p.sourceId
                   << " seq=" << p.seq
                   << " err_ms=" << err.GetMilliSeconds()
                   << " gt_used_ms=" << gtUsed.GetMilliSeconds());
    }
  }

  void ForwardFromRelay(uint32_t relay, PacketInfo p)
  {
    m_relayFwdTotal++;

    double eps = GetNodeEps(relay);
    Time nowGlobal = Simulator::Now();
    Time nowLocal = GlobalToLocal(nowGlobal, eps);

    NS_LOG_INFO("FWD Relay" << relay
                 << " src=" << p.sourceId
                 << " seq=" << p.seq
                 << " global=" << nowGlobal.GetSeconds() << "s"
                 << " local=" << nowLocal.GetSeconds() << "s");

    Simulator::Schedule(m_hopDelay,
                        &TreeMeshMetricsReady::ReceiveAtSink,
                        this,
                        m_sink,
                        relay,
                        p);
  }

  void ReceiveAtSink(uint32_t sink, uint32_t fromRelay, PacketInfo p)
  {
    m_sinkRxTotal++;

    double eps = GetNodeEps(sink);
    Time nowGlobal = Simulator::Now();
    Time nowLocal = GlobalToLocal(nowGlobal, eps);

    Time err = Seconds(0);
    Time gtUsed = Seconds(0);

    StreamWindow& w = m_expectedAtSink[p.sourceId];
    bool ok = CheckWindow(w, nowLocal, err, gtUsed);

    if (ok)
    {
      m_sinkRxOk++;

      Time e2eDelay = nowGlobal - p.createdAtGlobal;
      m_delaySumOk += e2eDelay;
      m_gtUsedSumOk += gtUsed;

      NS_LOG_INFO("RX_OK Sink" << sink
                   << " src=" << p.sourceId
                   << " seq=" << p.seq
                   << " via Relay" << fromRelay
                   << " err_ms=" << err.GetMilliSeconds()
                   << " gt_used_ms=" << gtUsed.GetMilliSeconds()
                   << " e2eDelayMs=" << e2eDelay.GetMilliSeconds());
    }
    else
    {
      m_sinkViol++;

      NS_LOG_INFO("VIOL Sink" << sink
                   << " src=" << p.sourceId
                   << " seq=" << p.seq
                   << " via Relay" << fromRelay
                   << " err_ms=" << err.GetMilliSeconds()
                   << " gt_used_ms=" << gtUsed.GetMilliSeconds());
    }
  }

  void SaveCsv()
  {
    std::ofstream out(m_csvPath, std::ios::out);

    double pdrOk = (m_txTotal == 0) ? 0.0
                                    : (100.0 * static_cast<double>(m_sinkRxOk) / static_cast<double>(m_txTotal));
    double plr = 100.0 - pdrOk;

    double avgDelayOkMs = (m_sinkRxOk == 0) ? 0.0
                                            : (1000.0 * m_delaySumOk.GetSeconds() / static_cast<double>(m_sinkRxOk));

    double avgGtUsedOkMs = (m_sinkRxOk == 0) ? 0.0
                                             : (1000.0 * m_gtUsedSumOk.GetSeconds() / static_cast<double>(m_sinkRxOk));

    out << "seed,run,gtModel,simTimeS,intervalS,hopDelayS,relayProcDelayS,"
           "srcPpm,relayPpm,sinkPpm,fixedGtMs,baseGtMs,gainK,minGtMs,maxGtMs,"
           "tx_total,relay_rx_total,relay_rx_ok,relay_viol,relay_fwd_total,"
           "sink_rx_total,sink_rx_ok,sink_viol,pdr_ok_percent,plr_percent,"
           "avg_delay_ok_ms,avg_gt_used_ok_ms\n";

    out << m_seed << ","
        << m_run << ","
        << m_gtModel << ","
        << std::fixed << std::setprecision(3)
        << m_simTime.GetSeconds() << ","
        << m_intervalLocal.GetSeconds() << ","
        << m_hopDelay.GetSeconds() << ","
        << m_relayProcDelayLocal.GetSeconds() << ","
        << m_srcPpm << ","
        << m_relayPpm << ","
        << m_sinkPpm << ","
        << m_fixedGtMs << ","
        << m_baseGtMs << ","
        << m_gainK << ","
        << m_minGtMs << ","
        << m_maxGtMs << ","
        << m_txTotal << ","
        << m_relayRxTotal << ","
        << m_relayRxOk << ","
        << m_relayViol << ","
        << m_relayFwdTotal << ","
        << m_sinkRxTotal << ","
        << m_sinkRxOk << ","
        << m_sinkViol << ","
        << std::setprecision(2) << pdrOk << ","
        << plr << ","
        << std::setprecision(3) << avgDelayOkMs << ","
        << avgGtUsedOkMs << "\n";

    out.close();
  }

  void PrintSummary()
  {
    double pdrOk = (m_txTotal == 0) ? 0.0
                                    : (100.0 * static_cast<double>(m_sinkRxOk) / static_cast<double>(m_txTotal));
    double plr = 100.0 - pdrOk;

    double avgDelayOkMs = (m_sinkRxOk == 0) ? 0.0
                                            : (1000.0 * m_delaySumOk.GetSeconds() / static_cast<double>(m_sinkRxOk));

    double avgGtUsedOkMs = (m_sinkRxOk == 0) ? 0.0
                                             : (1000.0 * m_gtUsedSumOk.GetSeconds() / static_cast<double>(m_sinkRxOk));

    NS_LOG_INFO("DONE Step 7.");
    NS_LOG_INFO("CSV saved to: " << m_csvPath);
    NS_LOG_INFO("TX_TOTAL=" << m_txTotal
                 << " RELAY_RX_OK=" << m_relayRxOk
                 << " RELAY_VIOL=" << m_relayViol
                 << " SINK_RX_OK=" << m_sinkRxOk
                 << " SINK_VIOL=" << m_sinkViol
                 << " PDR_OK%=" << pdrOk
                 << " PLR%=" << plr
                 << " AVG_DELAY_OK_MS=" << avgDelayOkMs
                 << " AVG_GT_USED_OK_MS=" << avgGtUsedOkMs);
  }

private:
  std::vector<uint32_t> m_sources;
  std::vector<uint32_t> m_relays;
  uint32_t m_sink;
  std::map<uint32_t, uint32_t> m_parent;
  std::map<uint32_t, uint32_t> m_sourceSeq;

  std::map<uint32_t, std::map<uint32_t, StreamWindow>> m_expectedAtRelay;
  std::map<uint32_t, StreamWindow> m_expectedAtSink;

  Time m_intervalLocal;
  Time m_simTime;
  Time m_hopDelay;
  Time m_relayProcDelayLocal;

  std::string m_gtModel;
  Time m_fixedGt;
  Time m_baseGt;
  double m_gainK;
  Time m_minGt;
  Time m_maxGt;

  double m_srcEps;
  double m_relayEps;
  double m_sinkEps;

  double m_srcPpm;
  double m_relayPpm;
  double m_sinkPpm;

  double m_fixedGtMs;
  double m_baseGtMs;
  double m_minGtMs;
  double m_maxGtMs;

  uint32_t m_seed;
  uint32_t m_run;

  std::string m_csvPath;

  uint64_t m_txTotal{0};
  uint64_t m_relayRxTotal{0};
  uint64_t m_relayRxOk{0};
  uint64_t m_relayViol{0};
  uint64_t m_relayFwdTotal{0};
  uint64_t m_sinkRxTotal{0};
  uint64_t m_sinkRxOk{0};
  uint64_t m_sinkViol{0};
  Time m_delaySumOk{Seconds(0)};
  Time m_gtUsedSumOk{Seconds(0)};
};

int
main(int argc, char* argv[])
{
  Time::SetResolution(Time::NS);

  bool verbose = true;
  double intervalS = 30.0;
  double simTimeS = 120.0;
  double hopDelayS = 0.050;
  double relayProcDelayS = 0.010;

  double srcPpm = 40.0;
  double relayPpm = 20.0;
  double sinkPpm = 0.0;

  std::string gtModel = "fixed";
  double fixedGtMs = 0.20;
  double baseGtMs = 0.05;
  double gainK = 0.50;
  double minGtMs = 0.01;
  double maxGtMs = 1.00;

  uint32_t seed = 1;
  uint32_t run = 1;

  std::string csvPath = "contrib/lora_drift_gt/results/phase1_step7_metrics_ready_fixed.csv";

  CommandLine cmd;
  cmd.AddValue("verbose", "Enable log output", verbose);
  cmd.AddValue("intervalS", "Source packet interval defined in local time (seconds)", intervalS);
  cmd.AddValue("simTimeS", "Simulation time (seconds)", simTimeS);
  cmd.AddValue("hopDelayS", "Per-hop propagation delay (seconds)", hopDelayS);
  cmd.AddValue("relayProcDelayS", "Relay processing delay in relay local time (seconds)", relayProcDelayS);
  cmd.AddValue("srcPpm", "Fixed drift level applied to source nodes (ppm)", srcPpm);
  cmd.AddValue("relayPpm", "Fixed drift level applied to relay nodes (ppm)", relayPpm);
  cmd.AddValue("sinkPpm", "Fixed drift level applied to sink node (ppm)", sinkPpm);
  cmd.AddValue("gtModel", "Guard-time model: fixed or proportional", gtModel);
  cmd.AddValue("fixedGtMs", "Fixed GT in ms (used when gtModel=fixed)", fixedGtMs);
  cmd.AddValue("baseGtMs", "Base GT in ms (used when gtModel=proportional)", baseGtMs);
  cmd.AddValue("gainK", "Proportional gain", gainK);
  cmd.AddValue("minGtMs", "Minimum proportional GT in ms", minGtMs);
  cmd.AddValue("maxGtMs", "Maximum proportional GT in ms", maxGtMs);
  cmd.AddValue("seed", "Scenario seed tag", seed);
  cmd.AddValue("run", "Scenario run tag", run);
  cmd.AddValue("csv", "CSV output path", csvPath);
  cmd.Parse(argc, argv);

  if (verbose)
  {
    LogComponentEnable("LoraDriftGt", LOG_LEVEL_INFO);
  }

  TreeMeshMetricsReady sim(intervalS,
                           simTimeS,
                           hopDelayS,
                           relayProcDelayS,
                           srcPpm,
                           relayPpm,
                           sinkPpm,
                           gtModel,
                           fixedGtMs,
                           baseGtMs,
                           gainK,
                           minGtMs,
                           maxGtMs,
                           seed,
                           run,
                           csvPath);
  sim.Run();

  return 0;
}
