#include "core/system/coredebug.h"
#include "presonus/noaa/programmer.hpp"
namespace presonus::noaa {
namespace {
class CclInformationServices final : public ProgrammerInformationServices {
public:
  void partID(std::uint32_t value) override {
    Core::DebugPrintf("Detected part ID = 0x%08X:\n", value);
  }
  void bootloaderVersion(std::uint32_t major, std::uint32_t minor) override {
    Core::DebugPrintf("Bootloader version = %d.%d\n", static_cast<int>(major),
                      static_cast<int>(minor));
  }
  void eraseCommand(unsigned char value) override {
    Core::DebugPrintf("Erase Command = 0x%2X\n",
                      static_cast<unsigned int>(value));
  }
};
} // namespace
ProgrammerInformationServices &cclProgrammerInformationServices() {
  static CclInformationServices services;
  return services;
}
} // namespace presonus::noaa
namespace Presonus::NOAA {
void TCardProgrammer::printInfo() {
  auto &services = information_
                       ? *information_
                       : presonus::noaa::cclProgrammerInformationServices();
  services.partID(state_.words28to40[0]);
  services.bootloaderVersion(state_.words28to40[1], state_.words28to40[2]);
  services.eraseCommand(static_cast<unsigned char>(state_.words28to40[3]));
}
std::int32_t TCardProgrammer::getChipID() {
  if (!doCommand(2)) {
    printProgress("IOCARD: chipidcmd err.", true);
    return 0;
  }
  if (waitResponse(2000) <= 0)
    return 0;
  state_.words28to40[0] =
      static_cast<std::uint32_t>(state_.response[1]) << 8 | state_.response[2];
  return 1;
}
std::int32_t TCardProgrammer::readInfo() {
  if (!doCommand(0)) {
    printProgress("IOCARD: getcmd err.", true);
    return 0;
  }
  if (waitResponse(2000) <= 0)
    return 0;
  const auto version = state_.response[1];
  state_.words28to40[1] = version >> 4;
  state_.words28to40[2] = version & 15;
  state_.words28to40[3] =
      (state_.words28to40[3] & 0xffffff00U) | state_.response[8];
  return getChipID();
}
} // namespace Presonus::NOAA
