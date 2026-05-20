#include "ns3/core-module.h"
#include "ns3/network-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("LoraDriftGt");

int
main(int argc, char *argv[])
{
  Time::SetResolution(Time::NS);

  bool verbose = true;
  CommandLine cmd;
  cmd.AddValue("verbose", "Enable log output", verbose);
  cmd.Parse(argc, argv);

  if (verbose)
  {
    LogComponentEnable("LoraDriftGt", LOG_LEVEL_INFO);
  }

  // Main manuscript-aligned mesh topology
  // Node 0 = Sink/Root
  // Node 1 = Relay1
  // Node 2 = Relay2
  // Node 3 = Source1
  // Node 4 = Source2
  // Node 5 = Source3
  //
  // Parent-child structure:
  // Source1 -> Relay1 -> Sink/Root
  // Source2 -> Relay1 -> Sink/Root
  // Source3 -> Relay2 -> Sink/Root

  NodeContainer nodes;
  nodes.Create(6);

  uint32_t sinkRoot = 0;
  uint32_t relay1   = 1;
  uint32_t relay2   = 2;
  uint32_t src1     = 3;
  uint32_t src2     = 4;
  uint32_t src3     = 5;

  NS_LOG_INFO("Phase 1 Step 2 OK: Main tree-based multi-hop LoRa mesh topology created.");
  NS_LOG_INFO("Node roles:");
  NS_LOG_INFO("  Sink/Root : node " << sinkRoot);
  NS_LOG_INFO("  Relay1    : node " << relay1);
  NS_LOG_INFO("  Relay2    : node " << relay2);
  NS_LOG_INFO("  Source1   : node " << src1);
  NS_LOG_INFO("  Source2   : node " << src2);
  NS_LOG_INFO("  Source3   : node " << src3);

  NS_LOG_INFO("Parent-child mesh structure:");
  NS_LOG_INFO("  Parent(Source1) = Relay1");
  NS_LOG_INFO("  Parent(Source2) = Relay1");
  NS_LOG_INFO("  Parent(Source3) = Relay2");
  NS_LOG_INFO("  Parent(Relay1)  = Sink/Root");
  NS_LOG_INFO("  Parent(Relay2)  = Sink/Root");

  NS_LOG_INFO("This step defines the main manuscript-aligned mesh structure only.");
  NS_LOG_INFO("Next step: implement parent-child forwarding behavior.");

  Simulator::Stop(Seconds(1.0));
  Simulator::Run();
  Simulator::Destroy();
  return 0;
}
