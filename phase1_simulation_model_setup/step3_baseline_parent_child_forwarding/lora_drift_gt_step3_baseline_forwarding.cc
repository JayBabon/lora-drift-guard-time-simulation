#include "ns3/core-module.h"
#include "ns3/network-module.h"

#include <fstream>
#include <iomanip>
#include <map>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("LoraDriftGt");

class TreeMeshBaseline
{
public:
  TreeMeshBaseline(double intervalS,
                   double simTimeS,
                   double hopDelayS,
                   double relayProcDelayS,
                   const std::string& csvPath)
      : m_interval(Seconds(intervalS)),
        m_simTime(Seconds(simTimeS)),
        m_hopDelay(Seconds(hopDelayS)),
        m_relayProcDelay(Seconds(relayProcDelayS)),
        m_csvPath(csvPath)
  {
    // Node roles
    m_sink = 0;
    m_relays = {1, 2};
    m_sources = {3, 4, 5};

    // Parent-child tree
    m_parent[3] = 1; // Source1 -> Relay1
    m_parent[4] = 1; // Source2 -> Relay1
    m_parent[5] = 2; // Source3 -> Relay2
    m_parent[1] = 0; // Relay1  -> Sink
    m_parent[2] = 0; // Relay2  -> Sink
  }

  void Run()
  {
    NS_LOG_INFO("Phase 1 Step 3: Baseline tree-based multi-hop LoRa mesh forwarding");
    NS_LOG_INFO("Sources generate packets, relays forward, sink collects.");

    for (auto src : m_sources)
    {
      m_sourceSeq[src] = 0;
      ScheduleNextSourceTx(src, Seconds(1.0));
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
    Time createdAt;
  };

  void ScheduleNextSourceTx(uint32_t src, Time when)
  {
    if (when < m_simTime)
    {
      Simulator::Schedule(when, &TreeMeshBaseline::SourceSend, this, src);
    }
  }

  void SourceSend(uint32_t src)
  {
    PacketInfo p;
    p.sourceId = src;
    p.seq = m_sourceSeq[src]++;
    p.createdAt = Simulator::Now();

    m_txTotal++;

    NS_LOG_INFO("TX Source" << src
                 << " seq=" << p.seq
                 << " at t=" << Simulator::Now().GetSeconds() << "s"
                 << " -> parent Relay" << m_parent[src]);

    uint32_t parent = m_parent[src];
    Simulator::Schedule(m_hopDelay,
                        &TreeMeshBaseline::ReceiveAtRelay,
                        this,
                        parent,
                        p);

    ScheduleNextSourceTx(src, Simulator::Now() + m_interval);
  }

  void ReceiveAtRelay(uint32_t relay, PacketInfo p)
  {
    m_relayRxTotal++;

    NS_LOG_INFO("RX Relay" << relay
                 << " packet from Source" << p.sourceId
                 << " seq=" << p.seq
                 << " at t=" << Simulator::Now().GetSeconds() << "s");

    Simulator::Schedule(m_relayProcDelay,
                        &TreeMeshBaseline::ForwardFromRelay,
                        this,
                        relay,
                        p);
  }

  void ForwardFromRelay(uint32_t relay, PacketInfo p)
  {
    m_relayFwdTotal++;

    uint32_t parent = m_parent[relay];

    NS_LOG_INFO("FWD Relay" << relay
                 << " forwarding Source" << p.sourceId
                 << " seq=" << p.seq
                 << " -> Sink/Root"
                 << " at t=" << Simulator::Now().GetSeconds() << "s");

    Simulator::Schedule(m_hopDelay,
                        &TreeMeshBaseline::ReceiveAtSink,
                        this,
                        parent,
                        relay,
                        p);
  }

  void ReceiveAtSink(uint32_t sink, uint32_t fromRelay, PacketInfo p)
  {
    m_sinkRxTotal++;

    Time delay = Simulator::Now() - p.createdAt;
    m_delaySum += delay;

    NS_LOG_INFO("RX Sink" << sink
                 << " got Source" << p.sourceId
                 << " seq=" << p.seq
                 << " via Relay" << fromRelay
                 << " at t=" << Simulator::Now().GetSeconds() << "s"
                 << " delay=" << delay.GetMilliSeconds() << " ms");
  }

  void SaveCsv()
  {
    std::ofstream out(m_csvPath, std::ios::out);
    out << "simTimeS,intervalS,hopDelayS,relayProcDelayS,tx_total,relay_rx_total,relay_fwd_total,sink_rx_total,pdr_percent,avg_delay_ms\n";

    double pdr = (m_txTotal == 0) ? 0.0
                                  : (100.0 * static_cast<double>(m_sinkRxTotal) / static_cast<double>(m_txTotal));

    double avgDelayMs = (m_sinkRxTotal == 0) ? 0.0
                                             : (1000.0 * m_delaySum.GetSeconds() / static_cast<double>(m_sinkRxTotal));

    out << std::fixed << std::setprecision(3)
        << m_simTime.GetSeconds() << ","
        << m_interval.GetSeconds() << ","
        << m_hopDelay.GetSeconds() << ","
        << m_relayProcDelay.GetSeconds() << ","
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

    NS_LOG_INFO("DONE Step 3.");
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

  Time m_interval;
  Time m_simTime;
  Time m_hopDelay;
  Time m_relayProcDelay;
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
  std::string csvPath = "contrib/lora_drift_gt/results/phase1_step3_mesh_baseline.csv";

  CommandLine cmd;
  cmd.AddValue("verbose", "Enable log output", verbose);
  cmd.AddValue("intervalS", "Source packet interval (seconds)", intervalS);
  cmd.AddValue("simTimeS", "Simulation time (seconds)", simTimeS);
  cmd.AddValue("hopDelayS", "Per-hop propagation delay (seconds)", hopDelayS);
  cmd.AddValue("relayProcDelayS", "Relay processing delay (seconds)", relayProcDelayS);
  cmd.AddValue("csv", "CSV output path", csvPath);
  cmd.Parse(argc, argv);

  if (verbose)
  {
    LogComponentEnable("LoraDriftGt", LOG_LEVEL_INFO);
  }

  TreeMeshBaseline sim(intervalS, simTimeS, hopDelayS, relayProcDelayS, csvPath);
  sim.Run();

  return 0;
}
