#include "presonus/mixer/WolverineRMLApplication.hpp"
namespace Presonus::Mixer {
void WolverineRMLApplication::getNetworkSetup(
    unsigned short &port, Presonus::UC::ServerInfo &info) const {
  port = 53000;
  info.strings[2] = "{49B355DA-B611-40A0-9955-EAB6F6DEACC7}";
  info.strings[0] = "StudioLive RML32 AI";
}
} // namespace Presonus::Mixer
