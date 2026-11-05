#include "core/public/corestringbuffer.h"
#include "presonus/noaa/programmer.hpp"
#include <algorithm>
#include <cstring>

namespace Presonus::NOAA {
// Portable source port: original ordinary return declarations and ARM layout
// remain unresolved. Calls use existing production serial and CCL providers.
std::int32_t TCardProgrammer::unprotect() {
  if (!doCommand(0x73)) {
    printProgress("IOCARD: cmd protect err.", true);
    return 0;
  }
  return waitAck(2000);
}
std::int32_t TCardProgrammer::eraseAll() {
  if (!doCommand(0x43)) {
    printProgress("IOCARD: EraseCmd Err.", true);
    return 0;
  }
  writeChar(0xff);
  writeChar(0);
  return waitAck(10000);
}
std::int32_t TCardProgrammer::writeImage() {
  auto &services =
      receive_ ? *receive_ : presonus::noaa::posixProgrammerReceiveServices();
  unsigned int offset = 0, address = 0x08000000;
  while (!state_.byte24 && offset < state_.length) {
    const auto count = std::min(256U, state_.length - offset);
    if (count < 256)
      services.debugMessage("NOAA ARM last partial packet\n");
    auto *packet = state_.response.packetData();
    std::memcpy(packet + 1, state_.image + offset, count);
    packet[0] = static_cast<unsigned char>(count - 1);
    if (!doCommand(0x31)) {
      printProgress("IOCARD: WriteCmd Err.", true);
      return 0;
    }
    sendAddress(address);
    address += count;
    offset += count;
    if (!waitAck(2000)) {
      printProgress("IOCARD: AddCmd Err.", true);
      return 0;
    }
    sendPacket(packet, static_cast<int>(count + 1));
    if (!waitAck(2000)) {
      printProgress("IOCARD: sendPacket Err.", true);
      return 0;
    }
    Core::CString64 message;
    message.appendFormat("writing address 0x%X", address);
    printProgress(message.getBuffer(), false);
  }
  printProgress("programming completed", true);
  return 1;
}
std::int32_t TCardProgrammer::update() {
  auto &services =
      receive_ ? *receive_ : presonus::noaa::posixProgrammerReceiveServices();
  presonus::noaa::setProgrammerProgressEpochMilliseconds(
      services.clockRawTicks() / 1000000);
  services.debugMessage("[*] Firmware image\n");
  Core::CString64 size;
  size.appendFormat("[*] Size (bytes): 0x%X\n", state_.length);
  services.debugMessage(size.getBuffer());
  services.debugMessage("[*] \n");
  printProgress("erasing flash", true);
  if (!eraseAll()) {
    printProgress("IOCARD: error erasing", true);
    return 2000;
  }
  if (!writeImage()) {
    printProgress("IOCARD: error image", true);
    return 2003;
  }
  printProgress("IOCARD: finished", true);
  return 0;
}
} // namespace Presonus::NOAA
