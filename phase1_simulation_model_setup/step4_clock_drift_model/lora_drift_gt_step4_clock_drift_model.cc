#include "ns3/core-module.h"
#include "ns3/network-module.h"

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

class TreeMeshDriftBaseline
{
public:
  TreeMeshDriftBaseline(double intervalS,
                        double simTimeS,
                        double hopDelayS,
                        double relayProcDelayS,
                        double srcPpm,
                        double relayPpm,
                        double sinkPpm,
                        const std::string& csvPath)
      : m_intervalLocal(Seconds(intervalS)),
        m_simTime(Seconds(simTimeS)),
        m_hopDelay(Seconds(hopDelayS)),
        m_relayProcDelayLocal(Seconds(relayProcDelayS)),
        m_srcEps(PpmToEps(srcPpm)),
        m_relayEps(PpmToEps(relayPpm)),
        m_sinkEps(PpmToEps(sinkPpm)),
        m_srcPpm(srcPpm),
        m_relayPpm(relayPpm),
        m_sinkPpm(sinkPpm),
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
    NS_LOG_INFO("Phase 1 Step 4: 6-node tree-based mesh with synchronization-error-based drift model");
    NS_LOG_INFO("Drift settings (ppm): src=" << m_srcPpm
                 << " relay=" << m_relayPpm
                 << " sink=" << m_sinkPpm);

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
      Simulator::Schedule(firstGlobal, &TreeMeshDriftBaseline::SourceSend, this, src);
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
                 << " ppm=" << m_srcPpm
                 << " -> Relay" << m_parent[src]);

    uint32_t relay = m_parent[src];
    Simulator::Schedule(m_hopDelay,
                        &TreeMeshDriftBaseline::ReceiveAtRelay,
                        this,
                        relay,
                        p);

    // Next send based on the source LOCAL clock
    Time nextLocal = nowLocal + m_intervalLocal;
    Time nextGlobal = LocalToGlobal(nextLocal, eps);

    if (nextGlobal < m_simTime)
    {
      Time delay = nextGlobal - Simulator::Now();
      if (delay.IsNegative())
      {
        delay = NanoSeconds(1);
      }
      Simulator::Schedule(delay, &TreeMeshDriftBaseline::SourceSend, this, src);
    }
  }

  void ReceiveAtRelay(uint32_t relay, PacketInfo p)
  {
    m_relayRxTotal++;

    double eps = GetNodeEps(relay);
    Time nowGlobal = Simulator::Now();
    Time nowLocal = GlobalToLocal(nowGlobal, eps);

    NS_LOG_INFO("RX Relay" << relay
                 << " packet from Source" << p.sourceId
                 << " seq=" << p.seq
                 << " global=" << nowGlobal.GetSeconds() << "s"
                 << " local=" << nowLocal.GetSeconds() << "s"
                 << " ppm=" << m_relayPpm);

    // Relay forwarding is also scheduled in LOCAL time
    Time fwdLocal = nowLocal + m_relayProcDelayLocal;
    Time fwdGlobal = LocalToGlobal(fwdLocal, eps);
    Time delay = fwdGlobal - Simulator::Now();
    if (delay.IsNegative())
    {
      delay = NanoSeconds(1);
    }

    Simulator::Schedule(delay,
                        &TreeMeshDriftBaseline::ForwardFromRelay,
                        this,
                        relay,
                        p);
  }

  void ForwardFromRelay(uint32_t relay, PacketInfo p)
  {
    m_relayFwdTotal++;

    double eps = GetNodeEps(relay);
    Time nowGlobal = Simulator::Now();
    Time nowLocal = GlobalToLocal(nowGlobal, eps);

    NS_LOG_INFO("FWD Relay" << relay
                 << " forwarding Source" << p.sourceId
                 << " seq=" << p.seq
                 << " global=" << nowGlobal.GetSeconds() << "s"
                 << " local=" << nowLocal.GetSeconds() << "s"
                 << " ppm=" << m_relayPpm
                 << " -> Sink/Root");

    Simulator::Schedule(m_hopDelay,
                        &TreeMeshDriftBaseline::ReceiveAtSink,
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
    Time e2eDelay = nowGlobal - p.createdAtGlobal;
    m_delaySum += e2eDelay;

    NS_LOG_INFO("RX Sink" << sink
                 << " got Source" << p.sourceId
                 << " seq=" << p.seq
                 << " via Relay" << fromRelay
                 << " global=" << nowGlobal.GetSeconds() << "s"
                 << " local=" << nowLocal.GetSeconds() << "s"
                 << " ppm=" << m_sinkPpm
                 << " e2eDelayMs=" << e2eDelay.GetMilliSeconds());
  }

  void SaveCsv()
  {
    std::ofstream out(m_csvPath, std::ios::out);
    out << "simTimeS,intervalS,hopDelayS,relayProcDelayS,srcPpm,relayPpm,sinkPpm,tx_total,relay_rx_total,relay_fwd_total,sink_rx_total,pdr_percent,avg_delay_ms\n";

    double pdr = (m_txTotal == 0) ? 0.0
                                  : (100.0 * static_cast<double>(m_sinkRxTotal) / static_cast<double>(m_txTotal));

    double avgDelayMs = (m_sinkRxTotal == 0) ? 0.0
                                             : (1000.0 * m_delaySum.GetSeconds() / static_cast<double>(m_sinkRxTotal));

    out << std::fixed << std::setprecision(3)
        << m_simTime.GetSeconds() << ","
        << m_intervalLocal.GetSeconds() << ","
        << m_hopDelay.GetSeconds() << ","
        << m_relayProcDelayLocal.GetSeconds() << ","
        << m_srcPpm << ","
        << m_relayPpm << ","
        << m_sinkPpm << ","
        << m_txTotal << ","
        << m_relayRxTotal << ","
        << m_relayFwdTotal << ","
        << m_sinkRxTotal << ","
        << std::setprecision(2) << pdr << ","
        << std::setprecision(3) << avgDelayMs << "\n";

    out.close();
  }

  void PrintSummary()
  {
    double pdr = (m_txTotal == 0) ? 0.0
                                  : (100.0 * static_cast<double>(m_sinkRxTotal) / static_cast<double>(m_txTotal));

    double avgDelayMs = (m_sinkRxTotal == 0) ? 0.0
                                             : (1000.0 * m_delaySum.GetSeconds() / static_cast<double>(m_sinkRxTotal));

    NS_LOG_INFO("DONE Step 4.");
    NS_LOG_INFO("CSV saved to: " << m_csvPath);
    NS_LOG_INFO("TX_TOTAL=" << m_txTotal
                 << " RELAY_RX_TOTAL=" << m_relayRxTotal
                 << " RELAY_FWD_TOTAL=" << m_relayFwdTotal
                 << " SINK_RX_TOTAL=" << m_sinkRxTotal
                 << " PDR%=" << pdr
                 << " AVG_DELAY_MS=" << avgDelayMs);
  }

private:
  std::vector<uint32_t> m_sources;
  std::vector<uint32_t> m_relays;
  uint32_t m_sink;
  std::map<uint32_t, uint32_t> m_parent;
  std::map<uint32_t, uint32_t> m_sourceSeq;

  Time m_intervalLocal;
  Time m_simTime;
  Time m_hopDelay;
  Time m_relayProcDelayLocal;

  double m_srcEps;
  double m_relayEps;
  double m_sinkEps;

  double m_srcPpm;
  double m_relayPpm;
  double m_sinkPpm;

  std::string m_csvPath;

  uint64_t m_txTotal{0};
  uint64_t m_relayRxTotal{0};
  uint64_t m_relayFwdTotal{0};
  uint64_t m_sinkRxTotal{0};
  Time m_delaySum{Seconds(0)};
};

int
main(int argc, char *argv[])
{
  Time::SetResolution(Time::NS);

  bool verbose = true;
  double intervalS = 30.0;
  double simTimeS = 120.0;
  double hopDelayS = 0.050;
  double relayProcDelayS = 0.010;

  // Step 4: fixed drift levels per scenario
  double srcPpm = 40.0;
  double relayPpm = 20.0;
  double sinkPpm = 0.0;

  std::string csvPath = "contrib/lora_drift_gt/results/phase1_step4_drift_baseline.csv";

  CommandLine cmd;
  cmd.AddValue("verbose", "Enable log output", verbose);
  cmd.AddValue("intervalS", "Source packet interval defined in local time (seconds)", intervalS);
  cmd.AddValue("simTimeS", "Simulation time (seconds)", simTimeS);
  cmd.AddValue("hopDelayS", "Per-hop propagation delay (seconds)", hopDelayS);
  cmd.AddValue("relayProcDelayS", "Relay processing delay in relay local time (seconds)", relayProcDelayS);
  cmd.AddValue("srcPpm", "Fixed drift level applied to source nodes (ppm)", srcPpm);
  cmd.AddValue("relayPpm", "Fixed drift level applied to relay nodes (ppm)", relayPpm);
  cmd.AddValue("sinkPpm", "Fixed drift level applied to sink node (ppm)", sinkPpm);
  cmd.AddValue("csv", "CSV output path", csvPath);
  cmd.Parse(argc, argv);

  if (verbose)
  {
    LogComponentEnable("LoraDriftGt", LOG_LEVEL_INFO);
  }

  TreeMeshDriftBaseline sim(intervalS,
                            simTimeS,
                            hopDelayS,
                            relayProcDelayS,
                            srcPpm,
                            relayPpm,
                            sinkPpm,
                            csvPath);
  sim.Run();

  return 0;
}
