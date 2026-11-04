#include "presonus/mixer/setup_property_applications.hpp"
namespace Presonus::Mixer {
presonus::mixer::AudioSetupRecord
StormApplication::getAudioEngineSetupProperty() const {
  return {{1634038640, 56, 32, 4, 14, 4, 4, 1, 0, 1, 4, 4, 16, 1}};
}
void RogueApplication::getNetworkSetup(unsigned short &port,
                                       UC::ServerInfo &info) const {
  port = 53000;
  info.strings[0] = "StudioLive 16.4.2AI";
  info.strings[2] = "{49B355DA-B613-40A0-9955-EAB6F6DEADD7}";
}
void StormApplication::getNetworkSetup(unsigned short &port,
                                       UC::ServerInfo &info) const {
  port = 53000;
  info.strings[0] = "StudioLive 32.4.2AI";
  info.strings[2] = "{BB9778E4-DF19-53E6-BCF3-8030F2435095}";
}
presonus::mixer::AudioSetupRecord
RogueApplication::getAudioEngineSetupProperty() const {
  return {{1634038640, 56, 16, 4, 6, 4, 4, 1, 0, 1, 4, 4, 8, 3}};
}
void WolverineApplication::getNetworkSetup(unsigned short &port,
                                           UC::ServerInfo &info) const {
  port = 53000;
  info.strings[0] = "StudioLive RM32 AI";
  info.strings[2] = "{49B355DA-B611-40A0-9955-EAB6F6DEACC7}";
}
presonus::mixer::AudioSetupRecord
GambitApplication::getAudioEngineSetupProperty() const {
  return {{1634038640, 56, 32, 2, 16, 4, 0, 1, 1, 1, 4, 4, 11, 9}};
}
void BeastApplication::getNetworkSetup(unsigned short &port,
                                       UC::ServerInfo &info) const {
  port = 53000;
  info.strings[0] = "StudioLive 24.4.2AI";
  info.strings[2] = "{62BA428D-20C2-B56A-1367-65DCDCA5D997}";
}
void GambitApplication::getNetworkSetup(unsigned short &port,
                                        UC::ServerInfo &info) const {
  port = 53000;
  info.strings[0] = "StudioLive RM16 AI";
  info.strings[2] = "{49B355DA-B612-40A0-9955-EAB6F6DEACB7}";
}
presonus::mixer::AudioSetupRecord
WolverineApplication::getAudioEngineSetupProperty() const {
  return {{1634038640, 56, 32, 2, 16, 4, 0, 1, 1, 1, 4, 4, 15, 8}};
}
presonus::mixer::AudioSetupRecord
BeastApplication::getAudioEngineSetupProperty() const {
  return {{1634038640, 56, 24, 4, 10, 4, 4, 1, 0, 1, 4, 4, 12, 2}};
}
} // namespace Presonus::Mixer
