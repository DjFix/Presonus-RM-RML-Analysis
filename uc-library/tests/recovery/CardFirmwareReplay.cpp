#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/dsp/audio_hal.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/surface_panel/OutputPin.hpp"
#include "presonus/uc/firmware_update_listener.hpp"
#include <atomic>
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <termios.h>
#include <thread>
#include <time.h>
#include <unistd.h>
#include <vector>
namespace {
thread_local std::vector<std::string> trace;
std::vector<unsigned> sleeps;
std::deque<unsigned char> serial;
int failOpen = 0, syncs = 0, closes = 0, writes = 0;
bool ignoredFailure = false;
bool serialOpened = false;
int previousByte = -1;
bool checksumPending = false;
std::int64_t ticks = 0;
void emit(const std::string &s) { trace.push_back(s); }
void queueOpen(bool fail) {
  serial.push_back(fail ? 0 : 0x79);
  if (fail)
    return;
  const unsigned char sequence[] = {0x79, 0,    0x10, 0, 0,    0,    0,   0, 0,
                                    0x43, 0x79, 0x79, 0, 0x12, 0x34, 0x79};
  serial.insert(serial.end(), std::begin(sequence), std::end(sequence));
}
struct Gpio : presonus::surface_panel_port::OutputPinIO,
              presonus::surface_panel_port::InputPinIO {
  struct File {
    int pin;
    bool value;
    bool input;
  };
  std::map<std::FILE *, File> files;
  unsigned next = 16;
  int selected = 0;
  std::FILE *open(const char *path, const char *mode) override {
    auto *f =
        reinterpret_cast<std::FILE *>(static_cast<std::uintptr_t>(next++));
    const std::string p(path);
    int pin = selected;
    if (p.find("/gpio/gpio") != std::string::npos) {
      const auto pos = p.find("/gpio/gpio") + 10;
      pin = std::stoi(p.substr(pos));
    }
    files.emplace(f, File{pin, p.find("/value") != std::string::npos,
                          std::string(mode) == "r"});
    if (files[f].value)
      emit(std::string(files[f].input ? "input:" : "output:") +
           std::to_string(pin));
    return f;
  }
  int printPin(std::FILE *, const char *, int p) override {
    selected = p;
    return 1;
  }
  int close(std::FILE *f) override {
    assert(files.count(f));
    const auto v = files.at(f);
    if (v.value)
      emit(std::string(v.input ? "input_destroy:" : "output_destroy:") +
           std::to_string(v.pin));
    files.erase(f);
    return 0;
  }
  void formatPath(char *p, std::size_t n, const char *fmt, int pin) override {
    std::snprintf(p, n, fmt, pin);
  }
  std::size_t write(const void *, std::size_t, std::size_t n,
                    std::FILE *) override {
    return n;
  }
  int buffering(std::FILE *, char *, int, std::size_t) override { return 0; }
  int put(int c, std::FILE *f) override {
    emit("set:" + std::to_string(files.at(f).pin) + ":" +
         std::to_string(c - '0'));
    return c;
  }
  int error() override { return 0; }
  void log(const char *) override { std::abort(); }
  void logSet(const char *, int, int) override { std::abort(); }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
};
struct Hal : Presonus::Dsp::IAudioHAL {
  void resetBoard(int a, int b) override {
    emit("reset:" + std::to_string(a) + ":" + std::to_string(b));
  }
  void enableDACs(bool, bool, int) override { std::abort(); }
  void enableAMP(bool) override { std::abort(); }
  void suspendControlSurfaces(bool) override { std::abort(); }
};
struct Response : presonus::dice::ResponseServices {
  presonus::noaa::CardState &state;
  explicit Response(presonus::noaa::CardState &s) : state(s) {}
  std::int64_t clockRawTicks() override { return (ticks += 100000000); }
  void pumpIdle(bool) override {
    state.observedWord20 = 1;
    state.observedWord28 = 1;
    state.observedWord40 = 1;
  }
  void sleepMilliseconds(std::uint32_t) override {}
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {}
};
struct Transport : presonus::noaa::SpiServiceIO {
  presonus::noaa::SpiPacketState &state;
  presonus::noaa::CardState *cardState = nullptr;
  int fpgaResult = 0;
  unsigned sequence = 0;
  explicit Transport(presonus::noaa::SpiPacketState &s) : state(s) {}
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { return 0; }
  std::int64_t rawTicks() override { return (ticks += 100000000); }
  void diagnostic(bool, const char *, int, bool) override {}
  int transfer(int fd, const presonus::noaa::SpiTransfer &t) override {
    assert(fd == 43);
    if (t.length < 2)
      return -1;
    const int stage = t.tx[1];
    if (stage >= 2 && stage <= 5) {
      assert(cardState && cardState->observedWord28 == 0 &&
             cardState->observedWord18 == 0 && cardState->observedWord24 == 0);
      Presonus::NOAA::SysexPacket reply;
      reply.length = 5;
      reply.bytes[1] = stage;
      reply.bytes[2] = 1;
      reply.bytes[3] = stage == 2 ? 127 : stage == 3 ? t.tx[3] : sequence;
      reply.bytes[4] = stage == 2 && fpgaResult == 2000   ? 3
                       : stage == 3 && fpgaResult == 2003 ? 3
                                                          : 0;
      if (stage == 3)
        sequence = (sequence + 1) & 127;
      for (int i = 0; i < state.receivers.count(); ++i) {
        auto *p = state.receivers[i];
        if (p->accepts(reply))
          p->receive(reply);
      }
    }
    return -1;
  }
};
struct Listener : Presonus::UC::IFirmwareUpdateListener {
  std::vector<std::string> messages;
  void onProgress(const char *s, float progress) override {
    if (s && std::string(s) == "restarting card") {
      unsigned bits;
      std::memcpy(&bits, &progress, 4);
      assert(bits == 0x3f733333);
    }
    if (s && std::string(s) == "finished")
      assert(progress == 1.f);
    messages.emplace_back(s ? s : "<null>");
  }
};
struct Card : Presonus::NOAA::TCard {
  bool mounted = true, compatible = true;
  Card(presonus::noaa::CardState &s, Response &r, Transport &t)
      : TCard(presonus::noaa::cardSetupTag, s, r, t) {}
  bool isMounted() override { return mounted; }
  bool isFirmwareCompatible(int m) override {
    assert(m >= 1 && m <= 3);
    return compatible;
  }
};
} // namespace
// System boundaries only: actual programmer/protocol/update/start/providers
// run. Accidental device/network/ioctl paths terminate, never forward to host.
extern "C" int __wrap_open(const char *p, int, ...) {
  assert(std::string(p) == "/dev/ttyS0");
  assert(!serialOpened);
  if (failOpen == 1) {
    errno = EACCES;
    return -1;
  }
  serialOpened = true;
  return 42;
}
extern "C" int __wrap_close(int fd) {
  assert(fd == 42 && serialOpened);
  serialOpened = false;
  ++closes;
  return 0;
}
extern "C" ssize_t __wrap_write(int fd, const void *p, size_t n) {
  assert(fd == 42 && serialOpened && n <= 257);
  ++writes;
  if (n == 1 && *static_cast<const unsigned char *>(p) == 0x7f) {
    ++syncs;
    queueOpen(syncs == failOpen);
    previousByte = -1;
    return n;
  }
  if (n == 1) {
    const int b = *static_cast<const unsigned char *>(p);
    if (checksumPending) {
      serial.push_back(0x79);
      checksumPending = false;
    } else if ((previousByte == 0x73 && b == 0x8c)) {
      serial.push_back(ignoredFailure ? 0 : 0x79);
      if (!ignoredFailure)
        serial.push_back(0x79);
    } else if ((previousByte == 0x43 && b == 0xbc) ||
               (previousByte == 0xff && b == 0) ||
               (previousByte == 0x31 && b == 0xce))
      serial.push_back(ignoredFailure && previousByte == 0x43 ? 0 : 0x79);
    previousByte = b;
  } else {
    assert(n == 4 || n == 5);
    checksumPending = true;
    previousByte = -1;
  }
  return static_cast<ssize_t>(n);
}
extern "C" ssize_t __wrap_read(int fd, void *p, size_t n) {
  assert(fd == 42 && serialOpened && n == 1);
  assert(!serial.empty());
  *static_cast<unsigned char *>(p) = serial.front();
  serial.pop_front();
  return 1;
}
extern "C" int __wrap_tcgetattr(int fd, termios *p) {
  assert(fd == 42);
  std::memset(p, 0, sizeof(*p));
  return 0;
}
extern "C" int __wrap_tcflush(int fd, int) {
  assert(fd == 42);
  return 0;
}
extern "C" int __wrap_tcsetattr(int fd, int, const termios *) {
  assert(fd == 42);
  return 0;
}
extern "C" int __wrap_ioctl(int, unsigned long, ...) { std::abort(); }
extern "C" int __wrap_socket(int, int, int) { std::abort(); }
extern "C" std::FILE *__wrap_fopen(const char *, const char *) { std::abort(); }
extern "C" int __wrap_clock_gettime(clockid_t, timespec *p) {
  ticks += 100000000;
  p->tv_sec = ticks / 1000000000;
  p->tv_nsec = ticks % 1000000000;
  return 0;
}
extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned n) {
  sleeps.push_back(n);
  emit("sleep:" + std::to_string(n));
}

int main(int argc, char **argv) {
  if (argc != 12)
    return 2;
  const std::string kind = argv[1];
  if (kind == "isolation") {
    std::atomic<unsigned> ready{0};
    auto check = [&ready](int pin) {
      Gpio first, second;
      auto *initial =
          presonus::surface_panel_port::setOutputPinConstructionIO(&first);
      ++ready;
      while (ready.load() != 2)
        std::this_thread::yield();
      assert(&presonus::surface_panel_port::outputPinConstructionIO() ==
             &first);
      {
        Presonus::Panel::OutputPin object(pin);
        assert(first.files.size() == 1);
        auto *prior =
            presonus::surface_panel_port::setOutputPinConstructionIO(&second);
        assert(prior == &first);
        {
          Presonus::Panel::OutputPin nested(pin + 1);
          assert(second.files.size() == 1);
        }
        assert(second.files.empty());
        presonus::surface_panel_port::setOutputPinConstructionIO(prior);
        object.set(1);
      }
      assert(first.files.empty());
      presonus::surface_panel_port::setOutputPinConstructionIO(initial);
    };
    std::thread one(check, 102), two(check, 103);
    one.join();
    two.join();
    std::cout << "{\"isolation\":true}\n";
    return 0;
  }
  const int mode = std::stoi(argv[2]), board = std::stoi(argv[3]);
  failOpen = std::stoi(argv[4]);
  ignoredFailure = std::stoi(argv[11]) != 0;
  Gpio gpio;
  auto *oldOut =
      presonus::surface_panel_port::setOutputPinConstructionIO(&gpio);
  auto *oldIn = presonus::surface_panel_port::setInputPinConstructionIO(&gpio);
  int result = 0;
  unsigned word44 = 0;
  std::vector<std::string> messages;
  if (kind == "reset" || kind == "cs") {
    presonus::panel_binding::PanelRegistrarPortState ps;
    Presonus::Panel::PanelRegistrar registrar(ps);
    registrar.resetBoard(kind == "cs" ? 0 : mode, board);
  } else {
    presonus::noaa::CardState state{};
    state.observedWord20 = std::stoul(argv[5]);
    state.observedWord28 = std::stoul(argv[6]);
    state.observedWord18 = 17;
    state.observedWord24 = 19;
    Hal hal;
    state.audioHal = &hal;
    state.opaque5c.value = &hal;
    Presonus::ResourceLibrary resources;
    const unsigned char image[] = {1, 2, 3, 4};
    // Real gzip bytes for a four-byte image, generated independently by zlib.
    std::vector<unsigned char> compressed(128);
    z_stream z{};
    assert(deflateInit2(&z, 6, Z_DEFLATED, 31, 8, Z_DEFAULT_STRATEGY) == Z_OK);
    z.next_in = const_cast<unsigned char *>(image);
    z.avail_in = 4;
    z.next_out = compressed.data();
    z.avail_out = compressed.size();
    assert(deflate(&z, Z_FINISH) == Z_STREAM_END);
    compressed.resize(z.total_out);
    assert(deflateEnd(&z) == Z_OK);
    resources.addFirmware("NOAA_S800ARM", 1, image, 4, false);
    resources.addFirmware("NOAA_S800FPGA", 1, compressed.data(),
                          compressed.size(), true);
    state.resources = &resources;
    presonus::noaa::SpiPacketState spiState({}, 0, 0, 8);
    Presonus::NOAA::TCardSPI spi(spiState);
    Transport transport(spiState);
    transport.fpgaResult = std::stoi(argv[10]);
    transport.cardState = &state;
    presonus::noaa::SpiServiceAccess::bind(spi, transport, 43, {}, 0);
    presonus::noaa::SpiServiceAccess::singleton(&spi);
    Response response(state);
    Listener listener;
    // For the real protocol, preload bytes after first-open handshake. Each
    // subsequent handshake appends its own response; unprotect/erase/image ACKs
    // are inserted before use below through scripted transport write semantics.
    {
      Card card(state, response, transport);
      card.mounted = std::stoi(argv[7]);
      card.compatible = std::stoi(argv[8]);
      if (kind == "precondition") {
        Presonus::ResourceLibrary invalid;
        if (board >= 4) {
          invalid.addFirmware("NOAA_S800ARM", 1, board == 5 ? nullptr : image,
                              board == 4 ? -1 : 4, false);
          invalid.addFirmware("NOAA_S800FPGA", 1, image, 4, false);
        }
        if (board == 0)
          state.audioHal = nullptr;
        if (board == 1)
          state.opaque5c.value = &invalid;
        if (board == 2)
          state.resources = nullptr;
        if (board >= 3)
          state.resources = &invalid;
        bool rejected = false;
        try {
          if (board < 2)
            card.eraseFirmware();
          else
            card.updateFirmware(nullptr, 2);
        } catch (const std::logic_error &) {
          rejected = true;
        }
        assert(rejected && trace.empty() && !serialOpened);
        result = 30000 + board;
      } else {
        result = kind == "erase"
                     ? card.eraseFirmware()
                     : card.updateFirmware(
                           std::stoi(argv[9]) ? &listener : nullptr, mode);
      }
      word44 = state.observedWord44;
      messages = listener.messages;
    }
    presonus::noaa::SpiServiceAccess::singleton(nullptr);
  }
  assert(!serialOpened && gpio.files.empty());
  presonus::surface_panel_port::setOutputPinConstructionIO(oldOut);
  presonus::surface_panel_port::setInputPinConstructionIO(oldIn);
  std::cout << "{\"return_value\":" << result << ",\"word44\":" << word44
            << ",\"closes\":" << closes << ",\"writes\":" << writes
            << ",\"syncs\":" << syncs << ",\"trace\":[";
  for (unsigned i = 0; i < trace.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << '"' << trace[i] << '"';
  }
  std::cout << "],\"messages\":[";
  for (unsigned i = 0; i < messages.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << '"' << messages[i] << '"';
  }
  std::cout << "]}\n";
}
