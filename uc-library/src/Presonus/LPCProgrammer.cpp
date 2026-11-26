#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cstdio>
#include <cstring>
#include <strings.h>

// Original internal helper identity. Its unusual remainder handling is
// retained. The caller supplies padded readable storage; this is not standard
// UU encoding.
[[gnu::used]] static unsigned raw_uu_encode(unsigned char *out, unsigned n,
                                            unsigned char *in) {
  unsigned remainder = n % 3, groups = n / 3 + remainder;
  for (unsigned i = 0; i < groups; ++i) {
    unsigned value = unsigned(in[0]) << 16;
    if (i != groups - 1 || remainder == 0) {
      value |= unsigned(in[1]) << 8;
      value |= in[2];
    } else if (remainder == 1) {
      value |= unsigned(in[1]) << 8;
    }
    for (unsigned k = 0; k < 4; ++k)
      out[k] = static_cast<unsigned char>(((value >> (18 - k * 6)) & 63) + 32);
    in += 3;
    out += 4;
  }
  return groups * 4;
}
namespace {
Core::int64 startMilliseconds{}; // Original translation-unit global start time.
Core::int64 milliseconds() {
  return Core::SystemClock::getTime() /
         static_cast<Core::int64>(Core::SystemClock::getFrequency() / 1000);
}
} // namespace
namespace Presonus {
LPCProgrammer::LPCProgrammer(const unsigned char *image, unsigned size)
    : originalLifecycle(true), borrowedImage(image) {
  imageState.raw08 = size;
  inputState.descriptor = 0;
}
LPCProgrammer::~LPCProgrammer() {
  if (originalLifecycle)
    close();
}
int LPCProgrammer::unlockFlash() {
  writeString("U 23130");
  return waitResult(0, 2000);
}
int LPCProgrammer::prepareSector(unsigned first, unsigned last) {
  Core::CString128 command;
  command.appendFormat("P %d %d", first, last);
  writeString(command);
  return waitResult(0, 100000);
}
int LPCProgrammer::eraseSector(unsigned first, unsigned last) {
  Core::CString128 command;
  command.appendFormat("E %d %d", first, last);
  writeString(command);
  return waitResult(0, 100000);
}
int LPCProgrammer::copyRAM2Flash(unsigned destination, unsigned source,
                                 unsigned size) {
  Core::CString128 command;
  command.appendFormat("C %d %d %d", destination, source, size);
  writeString(command);
  command.empty();
  command.appendFormat("PrgmFlash:%d %d %d", destination, source, size);
  printProgress(command);
  return waitResult(0, 100000);
}
void LPCProgrammer::printProgress(const char *message) {
  if (listener)
    listener->onProgress(
        message,
        static_cast<float>(milliseconds() - startMilliseconds) / 300000.f);
}
void LPCProgrammer::printInfo() {
  Core::DebugPrintf("[*] \n");
  Core::DebugPrintf("[*] Detected part ID = 0x%08X:\n", imageState.raw18);
  Core::DebugPrintf("[*]    Total number of 4k/32k ROM sectors: 0x%02X\n",
                    imageState.raw38);
  Core::DebugPrintf("[*]    Part serial no: 0x%08X %08X %08X %08X\n",
                    deviceIdentity.raw1c_to28[0], deviceIdentity.raw1c_to28[1],
                    deviceIdentity.raw1c_to28[2], deviceIdentity.raw1c_to28[3]);
  Core::DebugPrintf("[*]         Boot code: 0x%X\n", deviceIdentity.raw2c);
  Core::DebugPrintf("[*] \n");
}
int LPCProgrammer::open(const char *path) {
  if (!openPort(path)) {
    Core::DebugPrintf("DFU Error: could not open port\n");
    return 0;
  }
  if (!sync()) {
    Core::DebugPrintf("DFU Error: did not sync\n");
    return 0;
  }
  if (!readInfo()) {
    Core::DebugPrintf("DFU Error: read info failed\n");
    return 0;
  }
  if (!unlockFlash()) {
    Core::DebugPrintf("DFU Error: unlockFlash\n");
    return 0;
  }
  if (!initAddresses()) {
    Core::DebugPrintf("DFU Error: initAddresses\n");
    return 0;
  }
  printInfo();
  return 1;
}
int LPCProgrammer::eraseAll() {
  printProgress("erasing flash");
  prepareSector(imageState.raw40, imageState.raw48);
  eraseSector(imageState.raw40, imageState.raw48);
  printProgress("erasing sectors");
  return 0;
}
int LPCProgrammer::writeRAM(unsigned address, unsigned size,
                            unsigned char *data) {
  char command[128]{};
  std::snprintf(command, sizeof command, "W %d %d", address, size);
  writeString(command);
  if (!waitResult(0, 100000))
    return -1;
  if (data == block.data())
    std::memcpy(block.data() + 512, inputState.response.data(), 8);
  printProgress("Downloading packet...");
  const unsigned lines = size / 45 + (size % 45 != 0);
  const unsigned groups = lines / 20;
  unsigned char encoded[128]{};
  auto sendLine = [&](unsigned count, unsigned &checksum) {
    // Original zeros 62 bytes; oversized padded storage avoids host UB while
    // preserving each byte visible through its C-string transport.
    std::memset(encoded, 0, sizeof encoded);
    encoded[0] = static_cast<unsigned char>(count + 32);
    for (unsigned i = 0; i < count; ++i)
      checksum += data[i];
    raw_uu_encode(encoded + 1, count, data);
    std::snprintf(command, sizeof command, "%s", encoded);
    writeString(command);
  };
  for (unsigned g = 0; g < groups; ++g) {
    unsigned checksum = 0;
    for (unsigned i = 0; i < 20; ++i) {
      sendLine(45, checksum);
      data += 45;
      Core::Threads::CurrentThread::sleep(1);
    }
    std::snprintf(command, sizeof command, "%d", checksum);
    writeString(command);
    if (!waitResponse(100000))
      return 0;
    printProgress("CRC packet...");
    if (::strcasecmp(inputState.response.data(), "OK") != 0)
      std::printf("E: checksum (%d) NOT OK!\n", checksum);
  }
  unsigned checksum = 0;
  const unsigned tailLines = lines % 20;
  // SOURCE-PORT ADAPTATION: ceil(size/45) % 20 == 0 underflows the
  // native tail bound to UINT32_MAX (including zero and sizes856..900).
  // Return0 here instead; this branch is explicitly outside equivalence scope.
  if (tailLines == 0)
    return 0;
  for (unsigned i = 0; i < tailLines - 1; ++i) {
    sendLine(45, checksum);
    data += 45;
    Core::Threads::CurrentThread::sleep(1);
  }
  sendLine(size % 45, checksum);
  std::snprintf(command, sizeof command, "%d", checksum);
  writeString(command);
  if (!waitResponse(100000))
    return 0;
  int success = ::strcasecmp(inputState.response.data(), "OK") == 0;
  if (!success)
    std::printf("E: checksum (%d) NOT OK!\n", checksum);
  return success;
}
int LPCProgrammer::update(UC::IFirmwareUpdateListener *newListener) {
  listener = newListener;
  startMilliseconds = milliseconds();
  Core::DebugPrintf("[*] Firmware image\n");
  Core::DebugPrintf("[*]       Size (bytes): 0x%X\n", imageState.raw4c);
  Core::DebugPrintf("[*]   First ROM sector: 0x%X\n", imageState.raw40);
  Core::DebugPrintf("[*]    Last ROM sector: 0x%X of 0x%X\n",
                    imageState.raw30 + imageState.raw48, imageState.raw38);
  Core::DebugPrintf("[*] \n");
  eraseAll();
  unsigned offset = 0;
  unsigned end = imageState.raw30 + imageState.raw48;
  auto transfer = [&](unsigned sector, bool checksumFirst) {
    unsigned count = 512;
    if (offset + 512 > imageState.raw08) {
      block.fill(255);
      count = imageState.raw08 - offset;
    }
    std::memcpy(block.data(), borrowedImage + offset, count);
    if (checksumFirst && offset == 0) {
      std::memset(block.data() + 28, 0, 4);
      unsigned sum = 0;
      for (unsigned i = 0; i < 32; i += 4)
        sum += unsigned(block[i]) | (unsigned(block[i + 1]) << 8) |
               (unsigned(block[i + 2]) << 16) | (unsigned(block[i + 3]) << 24);
      sum = 0 - sum;
      for (unsigned i = 0; i < 4; ++i)
        block[28 + i] = static_cast<unsigned char>(sum >> (8 * i));
    }
    writeRAM(ramAddress, 512, block.data());
    prepareSector(sector, sector);
    copyRAM2Flash(imageState.raw34 + offset, ramAddress, 512);
    offset += count;
    Core::DebugPrintf(
        "[-] current sector: 0x%02X - 0x%08X of 0x%08X bytes written\r\n",
        sector, offset, imageState.raw08);
    std::fflush(stdout);
  };
  for (unsigned sector = imageState.raw30; sector < (end & 15); ++sector) {
    prepareSector(sector, sector);
    eraseSector(sector, sector);
    for (unsigned n = 0; n < 8; ++n) {
      Core::CString128 progress;
      progress.appendFormat("write block %d", n);
      printProgress(progress);
      if (static_cast<std::int32_t>(imageState.raw08 - offset) <= 0 &&
          offset + 512 > imageState.raw08) {
        block.fill(255);
        break;
      }
      transfer(sector, true);
    }
  }
  for (unsigned sector = 0; sector < ((end & 240) >> 4); ++sector)
    for (unsigned n = 0; n < 64; ++n)
      transfer(sector, false);
  Core::DebugPrintf("[*] done.\n");
  return 0;
}
} // namespace Presonus
