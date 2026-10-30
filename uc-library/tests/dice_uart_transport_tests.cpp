#include "presonus/dice/uart_assembly.hpp"
#include <array>
#include <cerrno>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Presonus::DICE::Dice3Uart;
using Presonus::DICE::SysexPacket;
struct Io {
  int result;
  std::string data;
  int error;
  bool disabled;
};
struct Case {
  std::string name, mode, span, payload;
  int count, receivers, mask, release, length;
  std::vector<Io> io;
  std::vector<std::int64_t> ticks;
};
std::ostringstream events;
bool recording = false;
void *diceLock = nullptr, *uartLock = nullptr;
int diceDepth = 0, uartDepth = 0;
Case *current = nullptr;
presonus::dice::UartAssemblyState *assembly = nullptr;
unsigned ioIndex = 0, clockIndex = 0;
void require(bool value) {
  if (!value)
    throw std::runtime_error("fixture contract failed");
}
std::string hex(const void *data, std::size_t size) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string out;
  for (std::size_t i = 0; i < size; ++i) {
    const auto b = static_cast<const unsigned char *>(data)[i];
    out += digits[b >> 4];
    out += digits[b & 15];
  }
  return out;
}
std::vector<unsigned char> decode(const std::string &text) {
  if (text == "-")
    return {};
  require(text.size() % 2 == 0);
  std::vector<unsigned char> out;
  for (std::size_t i = 0; i < text.size(); i += 2)
    out.push_back(
        static_cast<unsigned char>(std::stoul(text.substr(i, 2), nullptr, 16)));
  return out;
}
void packet(const SysexPacket &value) {
  events << unsigned(value.length) << ':'
         << hex(value.bytes.data(), value.length) << ':';
  const auto &words = value.portableMetadata().trailingWords;
  for (unsigned i = 0; i < 4; ++i) {
    if (i)
      events << ',';
    events << words[i];
  }
}
void lockEvent(void *p, bool locking) {
  if (!recording)
    return;
  require(p == diceLock || p == uartLock);
  int &depth = p == diceLock ? diceDepth : uartDepth;
  depth += locking ? 1 : -1;
  require(depth >= 0);
  events << 'L' << (p == diceLock ? 'D' : 'U') << (locking ? '+' : '-') << ';';
}
struct Callbacks : presonus::dice::AssemblyCallbacks {
  void noReceiver(unsigned type) override { events << 'N' << type << ';'; }
  void packetLog(const SysexPacket &value) override {
    events << 'P';
    packet(value);
    events << ';';
  }
  void sourcePortError(presonus::dice::AssemblyError error,
                       unsigned value) override {
    events << 'F' << static_cast<unsigned>(error) << ':' << value << ';';
  }
};
struct Receiver : Presonus::DICE::ISysexReceiver {
  unsigned index = 0;
  Dice3Uart *uart = nullptr;
  bool accepts(const SysexPacket &value) override {
    events << 'A' << index << ':';
    packet(value);
    events << ';';
    return (current->mask & (1 << index)) != 0;
  }
  void receive(const SysexPacket &value) override {
    events << 'R' << index << ':';
    packet(value);
    events << ';';
    if (current->release)
      uart->release();
  }
};
struct Services : presonus::panel::UartServices {
  Io next() {
    require(ioIndex < current->io.size());
    return current->io[ioIndex++];
  }
  int readFile(int descriptor, void *buffer, std::uint32_t size) override {
    require(descriptor == -1 && size == 64 && diceDepth > 0 && uartDepth > 0);
    const auto item = next();
    if (item.result > 0) {
      const auto data = decode(item.data);
      require(data.size() == static_cast<unsigned>(item.result) &&
              data.size() <= size);
      std::memcpy(buffer, data.data(), data.size());
    }
    events << 'I' << item.result << ':' << item.error << ':' << item.disabled
           << ';';
    errno = item.error;
    if (item.disabled)
      assembly->span()[64] = 1;
    return item.result;
  }
  int writeFile(int descriptor, const void *buffer,
                std::uint32_t size) override {
    require(descriptor == -1 &&
            size == static_cast<unsigned>(current->length) && diceDepth > 0 &&
            uartDepth > 0);
    const auto item = next();
    events << 'W' << size << ':' << hex(buffer, size) << ':' << item.result
           << ';';
    errno = item.error;
    if (item.disabled)
      assembly->span()[64] = 1;
    return item.result;
  }
  void printError(const char *prefix) override {
    require(std::string(prefix) == "UARTComm: ");
    events << "E;";
  }
  int openFile(const char *, int) override {
    throw std::runtime_error("no device open allowed");
  }
  int closeFile(int) override {
    throw std::runtime_error("no live close expected");
  }
  int exclusive(int, unsigned long) override {
    throw std::runtime_error("no ioctl allowed");
  }
  int getAttributes(int, termios &) override {
    throw std::runtime_error("no tcgetattr allowed");
  }
  void makeRaw(termios &) override {
    throw std::runtime_error("unexpected termios");
  }
  int setSpeed(termios &, speed_t) override {
    throw std::runtime_error("unexpected speed");
  }
  int setAttributes(int, int, const termios &) override {
    throw std::runtime_error("no tcsetattr allowed");
  }
  int setFlags(int, int, int) override {
    throw std::runtime_error("no fcntl allowed");
  }
  std::int64_t rawTicks() override {
    throw std::runtime_error("unexpected UART polling");
  }
};
} // namespace

extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *p) {
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
  lockEvent(p, true);
}
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *p) {
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
  lockEvent(p, false);
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  if (!recording)
    return;
  std::array<char, 1024> text;
  va_list args;
  va_start(args, format);
  const int size = std::vsnprintf(text.data(), text.size(), format, args);
  va_end(args);
  require(size >= 0 && static_cast<unsigned>(size) < text.size());
  events << 'G' << hex(text.data(), static_cast<unsigned>(size)) << ';';
}
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  require(recording && diceDepth > 0 && uartDepth == 0 &&
          clockIndex < current->ticks.size());
  const auto value = current->ticks[clockIndex++];
  events << 'C' << unsigned(assembly->count) << ':'
         << unsigned(assembly->span()[64]) << ':' << value << ';';
  return value;
}
} // namespace presonus::dice

int main() {
  unsigned count;
  if (!(std::cin >> count))
    return 2;
  for (unsigned index = 0; index < count; ++index) {
    Case c;
    unsigned ioCount, tickCount;
    std::cin >> c.name >> c.mode >> c.span >> c.count >> c.receivers >>
        c.mask >> c.release >> c.length >> c.payload >> ioCount;
    for (unsigned i = 0; i < ioCount; ++i) {
      Io item;
      std::cin >> item.result >> item.data >> item.error >> item.disabled;
      c.io.push_back(item);
    }
    std::cin >> tickCount;
    for (unsigned i = 0; i < tickCount; ++i) {
      std::int64_t value;
      std::cin >> value;
      c.ticks.push_back(value);
    }
    require(bool(std::cin));
    std::array<unsigned char, 67> seed;
    const auto span = decode(c.span);
    require(span.size() == seed.size());
    std::memcpy(seed.data(), span.data(), seed.size());
    presonus::dice::UartAssemblyState state(
        seed, static_cast<unsigned char>(c.count), 5);
    Callbacks callbacks;
    Services services;
    Dice3Uart uart(state, callbacks);
    presonus::panel::UartCommAccess::services(uart, services);
    std::array<Receiver, 2> receivers;
    require(c.receivers >= 0 && c.receivers <= 2);
    for (int i = 0; i < c.receivers; ++i) {
      receivers[i].index = i;
      receivers[i].uart = &uart;
      require(state.receivers.add(&receivers[i]));
    }
    SysexPacket value;
    value.length = static_cast<unsigned char>(c.length);
    const auto payload = decode(c.payload);
    require(payload.size() == value.bytes.size());
    std::memcpy(value.bytes.data(), payload.data(), payload.size());
    value.portableMetadata().trailingWords = {0x11223344, 0x55667788,
                                              0x99aabbcc, 0xddeeff00};
    current = &c;
    assembly = &state;
    diceLock = &state.lock;
    uartLock = &presonus::panel::ProtocolCommAccess::lock(uart);
    ioIndex = clockIndex = 0;
    diceDepth = uartDepth = 0;
    events.str("");
    events.clear();
    recording = true;
    if (c.mode == "p")
      uart.post(value);
    else if (c.mode == "i")
      uart.idleRead();
    else if (c.mode == "o")
      uart.onIdle();
    else if (c.mode == "x")
      uart.release();
    else
      throw std::runtime_error("invalid mode");
    require(diceDepth == 0 && uartDepth == 0);
    events << 'S' << unsigned(state.count) << ':' << hex(state.span(), 67)
           << ':' << ioIndex << ':' << clockIndex << ':';
    for (unsigned i = 0; i < 4; ++i) {
      if (i)
        events << ',';
      events << value.portableMetadata().trailingWords[i];
    }
    events << ';';
    recording = false;
    std::cout << c.name << ' ' << events.str() << '\n';
  }
}
