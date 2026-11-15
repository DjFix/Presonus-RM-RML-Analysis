#include "presonus/mixer/GambitRMLApplication.hpp"
namespace Presonus::Mixer {
void GambitRMLApplication::getNetworkSetup(
    unsigned short &port, Presonus::UC::ServerInfo &info) const {
  port = 53000;
  info.strings[2] = "{49B355DA-B612-40A0-9955-EAB6F6DEACB7}";
  info.strings[0] = "StudioLive RML16 AI";
}
} // namespace Presonus::Mixer
