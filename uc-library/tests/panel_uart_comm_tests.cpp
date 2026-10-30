#include "presonus/panel/uart_comm.hpp"
#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
using presonus::panel::ProtocolCommAccess;
using Presonus::Panel::UARTComm;
using presonus::panel::UartCommAccess;
std::ostringstream events;
bool recording = false;
void *deleteWatch = nullptr;
struct Case {
  std::string name, mode;
  int descriptor, size, result, opened, closed, exclusive, attributes, speed,
      applied, flags, high, timeout, overrideEnabled, overrideResult, seed;
  std::array<unsigned char, 60> attributeSeed;
  std::vector<std::pair<int, unsigned>> reads;
  std::vector<std::int64_t> times;
};
void require(bool value) {
  if (!value)
    throw std::runtime_error("UART fixture contract");
}
std::string hex(const void *data, std::size_t size) {
  const auto *bytes = static_cast<const unsigned char *>(data);
  constexpr char digits[] = "0123456789abcdef";
  std::string value;
  for (std::size_t i = 0; i < size; ++i) {
    value += digits[bytes[i] >> 4];
    value += digits[bytes[i] & 15];
  }
  return value;
}
struct Mock : presonus::panel::UartServices {
  Case &input;
  UARTComm *uart = nullptr;
  std::size_t readIndex = 0, timeIndex = 0;
  bool checked = false;
  explicit Mock(Case &value) : input(value) {}
  void probe() {
    if (!recording || checked || !uart)
      return;
    checked = true;
    bool acquired = false;
    std::thread worker([&] {
      auto &lock = ProtocolCommAccess::lock(*uart);
      acquired = lock.tryLock();
      if (acquired)
        lock.unlock();
    });
    worker.join();
    require(acquired == (input.mode == "n"));
  }
  int openFile(const char *path, int flags) override {
    probe();
    if (recording)
      events << "O" << hex(path, std::strlen(path)) << ':' << flags << ':'
             << input.opened << ';';
    return input.opened;
  }
  int closeFile(int descriptor) override {
    probe();
    if (recording)
      events << "X" << descriptor << ':' << input.closed << ';';
    return input.closed;
  }
  int readFile(int descriptor, void *buffer, std::uint32_t size) override {
    probe();
    int result = input.result;
    unsigned byte = unsigned(input.seed);
    if (input.mode == "n") {
      require(readIndex < input.reads.size());
      result = input.reads[readIndex].first;
      byte = input.reads[readIndex++].second;
    }
    std::vector<unsigned char> payload;
    if (result > 0) {
      require(std::uint32_t(result) <= size && result <= 128);
      for (int i = 0; i < result; ++i)
        payload.push_back(static_cast<unsigned char>(
            input.mode == "n" ? byte : input.seed + i * 11));
      std::memcpy(buffer, payload.data(), payload.size());
    }
    if (recording)
      events << "R" << descriptor << ':' << size << ':' << result << ':'
             << hex(payload.data(), payload.size()) << ';';
    return result;
  }
  int writeFile(int descriptor, const void *buffer,
                std::uint32_t size) override {
    probe();
    if (recording)
      events << "W" << descriptor << ':' << size << ':' << input.result << ':'
             << (size <= 128 ? hex(buffer, size) : "-") << ';';
    return input.result;
  }
  int exclusive(int descriptor, unsigned long request) override {
    probe();
    if (recording)
      events << "I" << descriptor << ':' << request << ':' << input.exclusive
             << ';';
    return input.exclusive;
  }
  int getAttributes(int descriptor, termios &value) override {
    probe();
    if (input.attributes != -1)
      std::memcpy(&value, input.attributeSeed.data(), sizeof(value));
    if (recording)
      events << "G" << descriptor << ':' << input.attributes << ';';
    return input.attributes;
  }
  void makeRaw(termios &value) override {
    probe();
    if (recording)
      events << "M" << hex(&value, sizeof(value)) << ':';
    // Pure libc memory transformation: no device or syscall is executed.
    ::cfmakeraw(&value);
    if (recording)
      events << hex(&value, sizeof(value)) << ';';
  }
  int setSpeed(termios &value, speed_t speed) override {
    probe();
    require(::cfsetspeed(&value, speed) == 0);
    if (recording)
      events << "S" << speed << ':' << input.speed << ':'
             << hex(&value, sizeof(value)) << ';';
    return input.speed;
  }
  int setAttributes(int descriptor, int action, const termios &value) override {
    probe();
    if (recording)
      events << "A" << descriptor << ':' << action << ':' << input.applied
             << ':' << hex(&value, sizeof(value)) << ';';
    return input.applied;
  }
  int setFlags(int descriptor, int command, int flags) override {
    probe();
    if (recording)
      events << "F" << descriptor << ':' << command << ':' << flags << ':'
             << input.flags << ';';
    return input.flags;
  }
  void printError(const char *prefix) override {
    probe();
    if (recording)
      events << "E" << hex(prefix, std::strlen(prefix)) << ';';
  }
  std::int64_t rawTicks() override {
    probe();
    require(timeIndex < input.times.size());
    const auto value = input.times[timeIndex++];
    if (recording)
      events << "T" << value << ';';
    return value;
  }
};
Mock *current = nullptr;
class Derived final : public UARTComm {};
class Override final : public UARTComm {
public:
  int enableHISpeed(bool enabled) override {
    require(current && enabled == false);
    current->probe();
    events << "V0:" << current->input.overrideResult << ';';
    return current->input.overrideResult;
  }
};
} // namespace

extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  if (!recording)
    return;
  if (current)
    current->probe();
  char buffer[4096];
  va_list arguments;
  va_start(arguments, format);
  const int count = std::vsnprintf(buffer, sizeof(buffer), format, arguments);
  va_end(arguments);
  require(count >= 0 && count < int(sizeof(buffer)));
  events << 'D' << hex(buffer, count) << ';';
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *pointer) {
  if (deleteWatch && pointer == deleteWatch) {
    if (recording)
      events << "Z;";
    deleteWatch = nullptr;
  }
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  if (deleteWatch && pointer == deleteWatch) {
    if (recording)
      events << "Z;";
    deleteWatch = nullptr;
  }
  __real__ZdlPvm(pointer, size);
}

int main() {
  static_assert(sizeof(termios) == 60 && offsetof(termios, c_cc) == 17);
  static_assert(offsetof(termios, c_cflag) == 8);
  static_assert(VTIME == 5 && VMIN == 6);
  static_assert(B115200 == 4098 && B230400 == 4099);
  static_assert((CLOCAL | CREAD | CS8) == 0x8b0);
  unsigned total;
  std::cin >> total;
  for (unsigned index = 0; index < total; ++index) {
    Case c;
    std::size_t reads, times;
    std::string attributes;
    std::cin >> c.name >> c.mode >> c.descriptor >> c.size >> c.result >>
        c.opened >> c.closed >> c.exclusive >> c.attributes >> c.speed >>
        c.applied >> c.flags >> c.high >> c.timeout >> c.overrideEnabled >>
        c.overrideResult >> c.seed >> reads >> times >> attributes;
    require(attributes.size() == 120);
    for (unsigned i = 0; i < 60; ++i)
      c.attributeSeed[i] = std::stoul(attributes.substr(i * 2, 2), nullptr, 16);
    for (std::size_t i = 0; i < reads; ++i) {
      int result;
      unsigned byte;
      std::cin >> result >> byte;
      c.reads.emplace_back(result, byte);
    }
    for (std::size_t i = 0; i < times; ++i) {
      std::int64_t value;
      std::cin >> value;
      c.times.push_back(value);
    }
    Mock services(c);
    current = &services;
    UARTComm *uart = c.mode == "c2" || c.mode == "d2"
                         ? static_cast<UARTComm *>(new Derived)
                     : c.overrideEnabled ? static_cast<UARTComm *>(new Override)
                                         : new UARTComm;
    services.uart = uart;
    UartCommAccess::services(*uart, services);
    if (c.mode != "c1" && c.mode != "c2")
      UartCommAccess::descriptor(*uart, c.descriptor);
    std::array<char, 128> data;
    for (unsigned i = 0; i < data.size(); ++i)
      data[i] = static_cast<char>(c.seed + i * 7);
    events.str("");
    events.clear();
    recording = true;
    int result = 0;
    std::string state, payload = "-";
    if (c.mode == "r") {
      result = uart->read(data.data(), c.size);
      payload = hex(data.data(), data.size());
    } else if (c.mode == "w")
      result = uart->write(data.data(), c.size);
    else if (c.mode == "o")
      result = uart->open("project-fixture-port");
    else if (c.mode == "x")
      uart->close();
    else if (c.mode == "h")
      result = uart->enableHISpeed(c.high != 0);
    else if (c.mode == "n")
      result = uart->getNextChar(c.timeout);
    else if (c.mode == "c1" || c.mode == "c2") {
      state = "C" + std::to_string(UartCommAccess::descriptor(*uart)) + ':' +
              std::to_string(unsigned(ProtocolCommAccess::receive(*uart)[0]));
      auto &lock = ProtocolCommAccess::lock(*uart);
      require(lock.tryLock());
      lock.unlock();
    } else if (c.mode == "d0") {
      deleteWatch = uart;
      delete static_cast<Presonus::Panel::ProtocolComm *>(uart);
      require(deleteWatch == nullptr);
      uart = nullptr;
      state = "dead";
    } else if (c.mode == "d1") {
      uart->~UARTComm();
      ::operator delete(uart);
      uart = nullptr;
      state = "dead";
    } else if (c.mode == "d2") {
      auto *derived = static_cast<Derived *>(uart);
      derived->~Derived();
      ::operator delete(derived);
      uart = nullptr;
      state = "dead";
    } else
      throw std::runtime_error("unknown fixture mode");
    if (state.empty())
      state = std::to_string(UartCommAccess::descriptor(*uart));
    recording = false;
    std::cout << c.name << ' ' << result << ':' << state << ':' << payload
              << ':' << events.str() << '\n';
    delete uart;
    current = nullptr;
  }
}
