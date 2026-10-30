#include "presonus/noaa/sysex_receiver.hpp"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <type_traits>

using presonus::noaa::SpiServiceAccess;
using Presonus::NOAA::SysexPacket;
using Presonus::NOAA::SysexReceiver;
using Presonus::NOAA::TCardSPI;
static_assert(std::is_abstract_v<SysexReceiver>);
static_assert(!std::has_virtual_destructor_v<SysexReceiver>);

static void checked(bool okay, int line) {
  if (!okay) {
    std::fprintf(stderr, "Receiver assertion line%d\n", line);
    std::abort();
  }
}
#define require(x) checked(bool(x), __LINE__)
static std::string hex(const unsigned char *data, std::size_t size) {
  static const char digits[] = "0123456789abcdef";
  std::string out;
  for (std::size_t i = 0; i < size; ++i) {
    out += digits[data[i] >> 4];
    out += digits[data[i] & 15];
  }
  return out;
}
struct Receiver : SysexReceiver {
  bool accepts(const SysexPacket &) override { return false; }
};
struct Record {
  Receiver *receiver = nullptr;
  SysexPacket *packet = nullptr;
  Core::Threads::Lock *lock = nullptr;
  std::string trace;
  int depth = 0, outcome = 0;
  std::int64_t ticks = 0;
  unsigned transfers = 0, clocks = 0, registered = 0, pinOpens = 0;
  void resetState() {
    require(receiver != nullptr);
    const auto &s = receiver->portableState();
    require(s.command == 0 && s.status == 0 && s.infoWords[0] == 0);
  }
  void event(const char *kind, std::initializer_list<std::string> args) {
    trace += kind;
    trace += '|';
    bool first = true;
    for (const auto &arg : args) {
      if (!first)
        trace += ',';
      trace += arg;
      first = false;
    }
    trace += ';';
  }
};
static Record *capture = nullptr;
extern "C" void
__real__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *);
extern "C" void
__real__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *);
extern "C" void
__wrap__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *p) {
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
  if (capture) {
    capture->resetState();
    require(static_cast<void *>(p) == static_cast<void *>(capture->lock));
    capture->event("K+", {std::to_string(++capture->depth)});
  }
}
extern "C" void
__wrap__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *p) {
  if (capture) {
    capture->resetState();
    require(static_cast<void *>(p) == static_cast<void *>(capture->lock));
    require(capture->depth > 0);
    capture->event("K-", {std::to_string(capture->depth--)});
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
}
extern "C" void __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *);
extern "C" void __wrap__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *p) {
  if (capture) {
    capture->resetState();
    auto *spi = SpiServiceAccess::singleton();
    require(spi != nullptr &&
            static_cast<Core::Portable::Deletable *>(spi) == p);
    capture->lock = &SpiServiceAccess::state(*spi).lock;
    ++capture->registered;
  }
  __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(p);
}
struct IO final : presonus::noaa::SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int fd, const presonus::noaa::SpiTransfer &t) override {
    require(capture != nullptr);
    auto &r = *capture;
    r.resetState();
    require(fd == -1 && t.length == r.packet->length);
    require(std::equal(t.tx, t.tx + t.length, r.packet->bytes.begin()));
    r.event("T", {std::to_string(fd), std::to_string(t.length),
                  std::to_string(t.speed), std::to_string(t.bits),
                  std::to_string(t.delay), std::to_string(t.csChange),
                  t.length ? hex(t.tx, t.length) : "-"});
    std::fill(t.rx, t.rx + t.length, 0xf8);
    ++r.transfers;
    return r.outcome;
  }
  int close(int) override { std::abort(); }
  int errorNumber() override {
    capture->resetState();
    capture->event("E", {"5"});
    return 5;
  }
  std::int64_t rawTicks() override {
    capture->resetState();
    ++capture->clocks;
    return capture->ticks;
  }
  void diagnostic(bool output, const char *format, int value,
                  bool argument) override {
    capture->resetState();
    capture->event("D", {std::to_string(output),
                         hex(reinterpret_cast<const unsigned char *>(format),
                             std::char_traits<char>::length(format)),
                         std::to_string(argument ? value : 0),
                         std::to_string(argument)});
  }
};
struct Pins final : presonus::surface_panel_port::InputPinIO {
  std::FILE *open(const char *path, const char *mode) override {
    capture->resetState();
    require(std::string(path) == "/sys/class/gpio/export" &&
            std::string(mode) == "a");
    ++capture->pinOpens;
    return nullptr;
  }
  int printPin(std::FILE *, const char *, int) override { std::abort(); }
  int close(std::FILE *) override { std::abort(); }
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
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
  void log(const char *s) override {
    capture->resetState();
    require(std::string(s) == "can't open gpio export\n");
  }
};
// These services are initialized before actual CCL's Deletable registry, hence
// remain alive for its real process-exit cleanup of registered singleton items.
static IO &io() {
  static IO value;
  return value;
}
static Pins &pins() {
  static Pins value;
  return value;
}
int main(int argc, char **argv) {
  require(argc == 2);
  auto &transport = io();
  auto &gpio = pins();
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    unsigned index, seed, command, status, word, length, singleton,
        expectedCommand, expectedStatus, expectedWord, lo, hi, transfers,
        clocks, allocated, registered;
    int outcome;
    std::int64_t ticks;
    std::string mode, packetText, trace;
    row >> index >> mode >> seed >> command >> status >> word >> length >>
        packetText >> singleton >> ticks >> outcome >> expectedCommand >>
        expectedStatus >> expectedWord >> lo >> hi >> transfers >> clocks >>
        trace >> allocated >> registered;
    require(bool(row) && packetText.size() == 512);
    Receiver receiver;
    require(receiver.portableState().command == 0 &&
            receiver.portableState().status == 0 &&
            receiver.portableState().infoWords[0] == 0);
    auto &state = receiver.portableState();
    if (mode[0] != 'C') {
      state.command = command;
      state.status = status;
      state.infoWords[0] = word;
    }
    state.infoWords[1] = 0x11223344;
    state.infoWords[2] = 0x55667788;
    state.rateWord = 0x99aabbcc;
    state.clockWord = 0xdeadbeef;
    SysexPacket packet;
    packet.length = length;
    for (unsigned i = 0; i < 256; ++i)
      packet.bytes[i] = std::stoul(packetText.substr(i * 2, 2), nullptr, 16);
    const auto before = packet.bytes;
    const unsigned seedWord = seed * 0x01010101U;
    packet.portableMetadata().trailingWords[2] = seedWord;
    packet.portableMetadata().trailingWords[3] = seedWord;
    Record record;
    record.receiver = &receiver;
    record.packet = &packet;
    record.ticks = ticks;
    record.outcome = outcome;
    if (mode[0] == 'C') {
      // C1/C2 native aliases are checked separately; this genuine derived
      // construction invokes the abstract base's real C2 initialization.
    } else if (mode == "R") {
      Presonus::NOAA::ISysexReceiver *base = &receiver;
      base->receive(packet);
    } else {
      require(mode == "P");
      std::array<unsigned char, 256> bytes{};
      presonus::noaa::SpiPacketState spiState(bytes, 0, 0, 0);
      TCardSPI borrowed(spiState);
      SpiServiceAccess::bind(borrowed, transport, -1, {}, 0);
      record.lock = singleton ? &spiState.lock : nullptr;
      SpiServiceAccess::singleton(singleton ? &borrowed : nullptr);
      auto *previousSPI =
          presonus::noaa::setSpiServiceConstructionIO(&transport);
      auto *previousPins =
          presonus::surface_panel_port::setInputPinConstructionIO(&gpio);
      capture = &record;
      receiver.post(packet);
      capture = nullptr;
      require(SpiServiceAccess::singleton() != nullptr);
      require(record.pinOpens == (allocated ? 2U : 0U));
      presonus::surface_panel_port::setInputPinConstructionIO(previousPins);
      presonus::noaa::setSpiServiceConstructionIO(previousSPI);
      SpiServiceAccess::singleton(nullptr);
    }
    const auto actualTrace =
        record.trace.empty()
            ? "-"
            : hex(reinterpret_cast<const unsigned char *>(record.trace.data()),
                  record.trace.size());
    const bool okay =
        state.command == expectedCommand && state.status == expectedStatus &&
        state.infoWords[0] == expectedWord &&
        state.infoWords[1] == 0x11223344 && state.infoWords[2] == 0x55667788 &&
        state.rateWord == 0x99aabbcc && state.clockWord == 0xdeadbeef &&
        packet.bytes == before && packet.length == length &&
        packet.portableMetadata().trailingWords[2] == lo &&
        packet.portableMetadata().trailingWords[3] == hi &&
        record.transfers == transfers && record.clocks == clocks &&
        record.registered == registered && record.depth == 0 &&
        actualTrace == trace;
    if (!okay) {
      std::fprintf(stderr, "Case%u %s mismatch: trace%s expected%s\n", index,
                   mode.c_str(), actualTrace.c_str(), trace.c_str());
      return 1;
    }
    ++cases;
  }
  require(input.eof() && cases > 0);
  std::printf(
      "PASS %u original ARM receiver cases with actual CCL/SPI composition\n",
      cases);
}
