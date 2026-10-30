#include "presonus/noaa/spi_packets.hpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

using presonus::noaa::SpiPacketState;
using presonus::noaa::SpiServiceAccess;
using Presonus::NOAA::SysexPacket;
using Presonus::NOAA::TCardSPI;
using Presonus::Panel::InputPin;
using Presonus::Panel::PinStateObserver;
using presonus::surface_panel_port::InputPinAccess;
using presonus::surface_panel_port::InputPinIO;
static void require(bool condition) {
  if (!condition)
    std::abort();
}
static std::string hex(const unsigned char *data, std::size_t length) {
  static const char *digits = "0123456789abcdef";
  std::string out;
  for (std::size_t i = 0; i < length; ++i) {
    out += digits[data[i] >> 4];
    out += digits[data[i] & 15];
  }
  return out;
}
static std::vector<unsigned char> unhex(const std::string &text) {
  std::vector<unsigned char> out;
  if (text == "-")
    return out;
  require(text.size() % 2 == 0);
  for (std::size_t i = 0; i < text.size(); i += 2)
    out.push_back(
        static_cast<unsigned char>(std::stoul(text.substr(i, 2), nullptr, 16)));
  return out;
}
struct Trace {
  Core::Threads::Lock *lock = nullptr;
  int depth = 0;
  std::string text;
  void event(const char *kind, const std::vector<std::string> &args) {
    text += kind;
    text += '|';
    for (unsigned i = 0; i < args.size(); ++i) {
      if (i)
        text += ',';
      text += args[i];
    }
    text += ';';
  }
};
static Trace *capture = nullptr;
extern "C" void
__real__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *);
extern "C" void
__real__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *);
extern "C" void
__wrap__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *lock) {
  __real__ZN4Core8Platform9PosixLock4lockEv(lock);
  if (capture) {
    require(static_cast<void *>(lock) == static_cast<void *>(capture->lock));
    capture->event("K+", {std::to_string(++capture->depth)});
  }
}
extern "C" void
__wrap__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *lock) {
  if (capture) {
    require(static_cast<void *>(lock) == static_cast<void *>(capture->lock) &&
            capture->depth > 0);
    capture->event("K-", {std::to_string(capture->depth--)});
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(lock);
}
struct Transaction {
  int result;
  bool release;
  std::vector<unsigned char> rx;
};
struct SPI final : presonus::noaa::SpiServiceIO {
  explicit SPI(Trace &t) : trace(t) {}
  Trace &trace;
  TCardSPI *spi = nullptr;
  int opened = 0, speed = 0, error = 0;
  std::int64_t ticks = 0;
  unsigned used = 0, clockCalls = 0;
  std::vector<Transaction> transactions;
  int open(const char *path, int flags) override {
    trace.event("O", {hex(reinterpret_cast<const unsigned char *>(path),
                          std::char_traits<char>::length(path)),
                      std::to_string(flags)});
    return opened;
  }
  int maxSpeed(int fd, std::uint32_t hz) override {
    trace.event("S", {std::to_string(fd), std::to_string(hz)});
    return speed;
  }
  int transfer(int fd, const presonus::noaa::SpiTransfer &t) override {
    trace.event("T", {std::to_string(fd), std::to_string(t.length),
                      std::to_string(t.speed), std::to_string(t.bits),
                      std::to_string(t.delay), std::to_string(t.csChange),
                      t.length ? hex(t.tx, t.length) : "-"});
    require(used < transactions.size());
    const auto &next = transactions[used++];
    require(next.rx.size() <= t.length);
    if (!next.rx.empty())
      std::memcpy(t.rx, next.rx.data(), next.rx.size());
    if (next.release)
      spi->release();
    return next.result;
  }
  int close(int) override { std::abort(); }
  int errorNumber() override {
    trace.event("E", {std::to_string(error)});
    return error;
  }
  std::int64_t rawTicks() override {
    ++clockCalls;
    return ticks;
  }
  void diagnostic(bool standard, const char *format, int value,
                  bool argument) override {
    trace.event("D", {std::to_string(standard),
                      hex(reinterpret_cast<const unsigned char *>(format),
                          std::char_traits<char>::length(format)),
                      std::to_string(argument ? value : 0),
                      std::to_string(argument)});
  }
};
struct PinInput {
  int number, state, last, sample;
};
struct Pins final : InputPinIO {
  explicit Pins(Trace &t) : trace(t) {}
  Trace &trace;
  std::vector<PinInput> input;
  static std::FILE *file(unsigned i) {
    return reinterpret_cast<std::FILE *>(std::uintptr_t(0x8000 + i * 256));
  }
  static unsigned id(std::FILE *p) {
    for (unsigned i = 1; i <= 2; ++i)
      if (file(i) == p)
        return i;
    std::abort();
  }
  std::FILE *open(const char *, const char *) override { std::abort(); }
  int printPin(std::FILE *, const char *, int) override { std::abort(); }
  int close(std::FILE *) override {
    require(capture == nullptr);
    return 0;
  }
  void formatPath(char *, std::size_t, const char *, int) override {
    std::abort();
  }
  std::size_t write(const void *, std::size_t, std::size_t,
                    std::FILE *) override {
    std::abort();
  }
  int buffering(std::FILE *, char *, int, std::size_t) override {
    std::abort();
  }
  void rewind(std::FILE *p) override {
    trace.event("W", {std::to_string(id(p))});
  }
  int flush(std::FILE *p) override {
    trace.event("F", {std::to_string(id(p))});
    return 0;
  }
  int get(std::FILE *p) override {
    auto i = id(p);
    trace.event("G",
                {std::to_string(i), std::to_string(input.at(i - 1).sample)});
    return input.at(i - 1).sample;
  }
  void notify(PinStateObserver *observer, int number, int value) override {
    observer->pinStateChanged(number, value);
  }
  void log(const char *) override { std::abort(); }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    unsigned index, disabled, pinCount;
    char mode;
    int fd, arg1, arg2;
    std::uint32_t count;
    std::int64_t ticks;
    Trace trace;
    SPI io(trace);
    Pins pinsIO(trace);
    row >> index >> mode >> fd >> count >> disabled >> ticks >> arg1 >> arg2 >>
        io.opened >> io.speed >> io.error >> pinCount;
    require(pinCount <= 2);
    pinsIO.input.resize(pinCount);
    for (auto &pin : pinsIO.input)
      row >> pin.number >> pin.state >> pin.last >> pin.sample;
    unsigned packetLength, transactionCount;
    std::string text;
    row >> packetLength >> text >> transactionCount;
    auto packetBytes = unhex(text);
    require(packetBytes.size() == packetLength);
    for (unsigned i = 0; i < transactionCount; ++i) {
      Transaction t;
      unsigned released, length;
      row >> t.result >> released >> length >> text;
      t.release = released;
      t.rx = unhex(text);
      require(t.rx.size() == length);
      io.transactions.push_back(std::move(t));
    }
    int expectedFd;
    std::uint32_t expectedCount, expectedDisabled, lo, hi, clocks, used, status;
    std::string expectedBytes, expectedTrace;
    row >> expectedFd >> expectedCount >> expectedDisabled >> lo >> hi >>
        clocks >> used >> status >> expectedBytes;
    std::vector<std::array<int, 3>> expectedPins(pinCount);
    for (auto &p : expectedPins)
      for (auto &v : p)
        row >> v;
    row >> expectedTrace;
    require(bool(row));
    std::array<unsigned char, 256> seed;
    for (unsigned i = 0; i < 256; ++i)
      seed[i] = static_cast<unsigned char>(i);
    SpiPacketState state(seed, count, static_cast<unsigned char>(disabled), 0);
    TCardSPI spi(state);
    io.spi = &spi;
    io.ticks = ticks;
    std::array<InputPin *, 32> pinList{};
    std::vector<std::unique_ptr<InputPin>> pins;
    for (unsigned i = 0; i < pinCount; ++i) {
      pins.push_back(std::make_unique<InputPin>(-1, nullptr));
      pinList[i] = pins.back().get();
      const auto &p = pinsIO.input[i];
      InputPinAccess::bind(*pinList[i], pinsIO, p.number, p.state, p.last,
                           Pins::file(i + 1),
                           static_cast<PinStateObserver *>(&spi));
    }
    SpiServiceAccess::bind(spi, io, fd, pinList, pinCount);
    SysexPacket packet;
    packet.length = static_cast<unsigned char>(packetLength);
    std::copy(packetBytes.begin(), packetBytes.end(), packet.bytes.begin());
    packet.portableMetadata().trailingWords[2] = 0xaabbccdd;
    packet.portableMetadata().trailingWords[3] = 0x11223344;
    trace.lock = &state.lock;
    capture = &trace;
    unsigned result = 0;
    if (mode == 'O')
      result = static_cast<unsigned>(spi.open("/dev/spidev0.0"));
    else if (mode == 'P')
      spi.post(packet);
    else if (mode == 'I')
      spi.idleRead();
    else if (mode == 'N')
      spi.idleReadPin();
    else if (mode == 'A')
      spi.onIdle(arg1 != 0);
    else if (mode == 'C')
      spi.pinStateChanged(arg1, arg2);
    else
      std::abort();
    capture = nullptr;
    bool okay =
        SpiServiceAccess::descriptor(spi) == expectedFd &&
        state.count == expectedCount && state.disabled == expectedDisabled &&
        packet.portableMetadata().trailingWords[2] == lo &&
        packet.portableMetadata().trailingWords[3] == hi &&
        io.clockCalls == clocks && io.used == used && result == status &&
        hex(state.span(), 256) == expectedBytes &&
        (trace.text.empty()
             ? "-"
             : hex(reinterpret_cast<const unsigned char *>(trace.text.data()),
                   trace.text.size())) == expectedTrace &&
        trace.depth == 0 &&
        std::equal(packetBytes.begin(), packetBytes.end(),
                   packet.bytes.begin());
    for (unsigned i = 0; i < pinCount; ++i)
      okay = okay &&
             InputPinAccess::number(*pinList[i]) == expectedPins[i][0] &&
             InputPinAccess::state(*pinList[i]) == expectedPins[i][1] &&
             InputPinAccess::last(*pinList[i]) == expectedPins[i][2] &&
             InputPinAccess::observer(*pinList[i]) ==
                 static_cast<PinStateObserver *>(&spi);
    if (!okay) {
      std::fprintf(
          stderr, "Mismatch case%u mode%c actual trace%s expected%s\n", index,
          mode,
          hex(reinterpret_cast<const unsigned char *>(trace.text.data()),
              trace.text.size())
              .c_str(),
          expectedTrace.c_str());
      return 1;
    }
    ++cases;
  }
  require(input.eof() && cases > 0);
  std::printf("PASS: %u original ARM SPI operation cases with actual CCL "
              "recursive lock and real parser/InputPin callback composition\n",
              cases);
}
