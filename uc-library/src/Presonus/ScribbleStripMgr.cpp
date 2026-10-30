#include "presonus/surface/ScribbleStripMgr.hpp"
#include "core/system/coredebug.h"
#include "core/system/corethread.h"
#include "presonus/surface_panel/OutputPin.hpp"
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>
namespace {
const char *const devices[] = {"/dev/spidev1.0", "/dev/spidev1.1",
                               "/dev/spidev1.6", "/dev/spidev1.7"};
}
namespace Presonus {
ScribbleStripMgr::ScribbleStripMgr() { initDisplayModules(); }
void ScribbleStripMgr::txCommandDataArray(int fd, unsigned char command,
                                          unsigned char *data, int count) {
  unsigned char byte = 0x30;
  spi_ioc_transfer transfer{};
  transfer.tx_buf = reinterpret_cast<std::uintptr_t>(&byte);
  transfer.len = 1;
  ioctl(fd, SPI_IOC_MESSAGE(1), &transfer);
  byte = command;
  Panel::OutputPin dc(30);
  dc.set(0);
  transfer = {};
  transfer.tx_buf = reinterpret_cast<std::uintptr_t>(&byte);
  transfer.len = 1;
  ioctl(fd, SPI_IOC_MESSAGE(1), &transfer);
  dc.set(1);
  if (count > 0) {
    transfer = {};
    transfer.tx_buf = reinterpret_cast<std::uintptr_t>(data);
    transfer.len = count;
    ioctl(fd, SPI_IOC_MESSAGE(1), &transfer);
  }
}
int ScribbleStripMgr::writeToScribbleStrip(int display,
                                           const Core::BitmapData &data) {
  if (display < 0) {
    Core::DebugPrintf("ScribbleStripMgr::writeToScribbleStrip display number "
                      "%d out of range\n",
                      display);
    return 1;
  }
  const auto *source = static_cast<const unsigned char *>(data.scan0);
  for (int y = 0; y != 96; y += 8)
    for (int x = 0; x != 64; ++x) {
      unsigned char value = 0;
      for (int bit = 0; bit != 8; ++bit)
        if (source[data.rowBytes * (y + bit) + (x >> 3)] & (128 >> (x & 7)))
          value |= 128 >> bit;
      buffer[y * 8 + x] = value;
    }
  const char *path = devices[(display >> 2) & 3];
  int fd = open(path, O_WRONLY);
  if (fd == -1) {
    Core::DebugPrintf("writeToScribbleStrip failed to open device %s [%s]\n",
                      path, strerror(errno));
    return 0;
  }
  unsigned char range[] = {static_cast<unsigned char>((display & 3) * 64),
                           static_cast<unsigned char>((display & 3) * 64 + 63)};
  txCommandDataArray(fd, 0x15, range, 2);
  range[0] = 4;
  range[1] = 16;
  txCommandDataArray(fd, 0x75, range, 2);
  txCommandDataArray(fd, 0x5c, buffer.data(), 768);
  close(fd);
  return 1;
}
void ScribbleStripMgr::initDisplayModules() {
  Panel::OutputPin reset(29);
  reset.set(0);
  Core::Threads::CurrentThread::sleep(100);
  reset.set(1);
  Core::Threads::CurrentThread::sleep(500);
  struct Command {
    unsigned char command;
    unsigned char length;
    unsigned char data[8];
  };
  const Command commands[] = {{0x31, 0, {}},
                              {0xd7, 1, {0x9f}},
                              {0xe0, 1, {0}},
                              {0xe3, 0, {}},
                              {0xe1, 0, {}},
                              {0x30, 0, {}},
                              {0xd2, 0, {}},
                              {0xd1, 0, {}},
                              {0x94, 0, {}},
                              {0xae, 0, {}},
                              {0x20, 1, {0}},
                              {0x20, 1, {0x0b}},
                              {0x81, 2, {0x13, 4}},
                              {0x31, 0, {}},
                              {0x32, 3, {0, 1, 2}},
                              {0x30, 0, {}},
                              {0xf0, 1, {0x10}},
                              {0xca, 3, {0, 0x7f, 0}},
                              {8, 0, {}},
                              {0xab, 1, {0}},
                              {0xbc, 1, {0}},
                              {0xa6, 0, {}},
                              {0x31, 0, {}},
                              {0x40, 0, {}},
                              {0xf0, 4, {0x1f, 0x1f, 0x1f, 0x1f}},
                              {0xf2, 3, {0x1e, 0x28, 0x32}},
                              {0xf4, 8, {}},
                              {0x30, 0, {}}};
  for (const char *path : devices) {
    int fd = open(path, O_WRONLY);
    if (fd == -1) {
      Core::DebugPrintf("initDisplayModules failed to open device %s [%s]\n",
                        path, strerror(errno));
      continue;
    }
    for (unsigned i = 0; i < sizeof(commands) / sizeof(commands[0]); ++i) {
      auto command = commands[i];
      txCommandDataArray(fd, command.command, command.data, command.length);
      if (i == 2)
        Core::Threads::CurrentThread::sleep(10);
      if (i == 3 || i == 6)
        Core::Threads::CurrentThread::sleep(20);
      if (i == 10)
        Core::Threads::CurrentThread::sleep(50);
    }
    unsigned char zero[3072]{};
    unsigned char range[] = {0, 255};
    txCommandDataArray(fd, 0x76, range, 0);
    txCommandDataArray(fd, 0x15, range, 2);
    range[0] = 4;
    range[1] = 16;
    txCommandDataArray(fd, 0x75, range, 2);
    txCommandDataArray(fd, 0x5c, zero, 3072);
    txCommandDataArray(fd, 0xaf, range, 0);
    close(fd);
  }
}
} // namespace Presonus
