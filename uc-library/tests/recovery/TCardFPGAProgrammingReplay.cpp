#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/noaa/TCardFPGAUpdater.hpp"
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

namespace presonus::application {
struct ResourceAccess {
  static void set(Presonus::FirmwareBundle &b,
                  const std::vector<unsigned char> &s, bool compressed) {
    b.image_ = s.data();
    b.image_size_ = static_cast<int>(s.size());
    b.compressed_ = compressed;
    b.stream_ = {};
  }
};
} // namespace presonus::application
namespace {
unsigned opens = 0, closes = 0, reads = 0;
std::string quote(const std::string &s) {
  std::string out = "\"";
  for (unsigned char c : s) {
    if (c == '"' || c == '\\')
      out += '\\';
    if (c == '\n')
      out += "\\n";
    else if (c == '\r')
      out += "\\r";
    else
      out += static_cast<char>(c);
  }
  return out + "\"";
}
std::string hex(const unsigned char *s, unsigned n) {
  const char *digits = "0123456789abcdef";
  std::string out;
  for (unsigned i = 0; i < n; ++i) {
    out += digits[s[i] >> 4];
    out += digits[s[i] & 15];
  }
  return out;
}
template <class T> void numbers(const std::vector<T> &v) {
  std::cout << '[';
  bool first = true;
  for (auto &x : v) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << x;
  }
  std::cout << ']';
}
void strings(const std::vector<std::string> &v) {
  std::cout << '[';
  bool first = true;
  for (auto &x : v) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << quote(x);
  }
  std::cout << ']';
}
struct Listener : Presonus::UC::IFirmwareUpdateListener {
  std::vector<std::string> messages;
  std::vector<float> fractions;
  void onProgress(const char *s, float value) override {
    messages.push_back(s ? s : "<null>");
    fractions.push_back(value);
  }
};
struct Services : presonus::noaa::FpgaUpdaterServices {
  Presonus::NOAA::TCardFPGAUpdater *updater = nullptr;
  bool posted = false, delegated = false, delegateReply = false;
  std::int64_t start = 100, step = 400;
  int after = 0, tick = 0;
  unsigned reply = 0, status = 0;
  std::vector<std::string> debug;
  std::vector<unsigned> sleeps, pumps;
  unsigned notices = 0;
  void receive() {
    Presonus::NOAA::SysexPacket p;
    p.bytes[2] = 1;
    p.bytes[3] = reply;
    p.bytes[4] = status;
    updater->receive(p);
  }
  std::int64_t clockRawTicks() override {
    if (!posted)
      return 100000000;
    const int index = tick++;
    if (after >= 0 && index >= after)
      receive();
    return (start + index * step) * 1000000;
  }
  void pumpIdle(bool force) override {
    assert(delegated);
    pumps.push_back(force);
    if (delegateReply)
      updater->portableState().infoWords[0] = 7;
    // Delegated actual provider uses this monotonic fixture service too.
    posted = true;
    after = -1;
  }
  void sleepMilliseconds(std::uint32_t n) override { sleeps.push_back(n); }
  void timeoutNotice(bool response, std::uint32_t, std::uint32_t) override {
    assert(delegated && response);
    ++notices;
  }
  void debugMessage(const char *s) override { debug.push_back(s); }
};
struct Transport : presonus::noaa::SpiServiceIO {
  Services &services;
  std::string fault;
  int replyAfter;
  unsigned sequence = 0;
  std::vector<std::string> packets;
  explicit Transport(Services &s, std::string f, int after)
      : services(s), fault(std::move(f)), replyAfter(after) {}
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int close(int) override { std::abort(); }
  std::int64_t rawTicks() override { return 100000000; }
  int errorNumber() override { return 0; }
  void diagnostic(bool, const char *, int, bool) override {}
  int transfer(int fd, const presonus::noaa::SpiTransfer &t) override {
    assert(fd == 42 && t.length <= 255);
    packets.push_back(hex(t.tx, t.length));
    auto &state = services.updater->portableState();
    assert(state.command == 0 && state.status == 0 && state.infoWords[0] == 0);
    const int stage = t.length > 1 ? t.tx[1] : -1;
    unsigned reply = stage == 2 ? 127 : stage == 3 ? t.tx[3] : sequence & 127;
    if (stage == 3)
      sequence = (sequence + 1) & 127;
    const bool target =
        (stage == 2 && fault.find("erase") == 0) ||
        (stage == 3 && packets.size() == 2 && fault.find("block") == 0) ||
        (stage == 5 && fault.find("finish") == 0);
    services.status =
        target && fault.find("status") != std::string::npos ? 3 : 0;
    if (target && fault.find("seq") != std::string::npos)
      reply = (reply + 1) & 255;
    services.reply = reply;
    services.tick = 0;
    services.posted = true;
    services.after =
        target && fault.find("timeout") != std::string::npos ? -1 : replyAfter;
    if (services.after == 0)
      services.receive();
    // All data is captured in memory. The real post provider's transfer failure
    // path returns immediately; no idle/device/network/serial calls can follow.
    return -1;
  }
};
} // namespace
// Any accidental attempt to reach a default hardware path aborts the replay.
extern "C" int __wrap_open(const char *, int, ...) { std::abort(); }
extern "C" int __wrap_ioctl(int, unsigned long, ...) { std::abort(); }
extern "C" int __wrap_socket(int, int, int) { std::abort(); }
extern "C" int __real_inflateInit2_(z_streamp, int, const char *, int);
extern "C" int __wrap_inflateInit2_(z_streamp p, int w, const char *v, int n) {
  ++opens;
  return __real_inflateInit2_(p, w, v, n);
}
extern "C" int __real_inflate(z_streamp, int);
extern "C" int __wrap_inflate(z_streamp p, int f) {
  ++reads;
  return __real_inflate(p, f);
}
extern "C" int __real_inflateEnd(z_streamp);
extern "C" int __wrap_inflateEnd(z_streamp p) {
  ++closes;
  return __real_inflateEnd(p);
}
int main(int argc, char **argv) {
  if (argc != 13)
    return 2;
  const std::string mode = argv[1], fault = argv[3];
  const unsigned size = std::stoul(argv[2]);
  Services services;
  services.start = std::stoll(argv[4]);
  services.step = std::stoll(argv[5]);
  const int after = std::stoi(argv[6]);
  const bool cancelled = std::stoi(argv[7]);
  const int length = std::stoi(argv[8]);
  const bool null = std::stoi(argv[9]);
  const auto timeout = std::stoll(argv[10]);
  const int message = std::stoi(argv[11]);
  services.delegateReply = std::stoi(argv[12]);
  services.delegated = mode == "wait" && (null || length == 0);
  Listener listener;
  std::vector<unsigned char> image(size);
  for (unsigned i = 0; i < size; ++i)
    image[i] = (i * 73 + 19) & 255;
  std::vector<unsigned char> compressed(compressBound(size) + 64);
  z_stream z{};
  assert(deflateInit2(&z, 6, Z_DEFLATED, 31, 8, Z_DEFAULT_STRATEGY) == Z_OK);
  z.next_in = image.data();
  z.avail_in = size;
  z.next_out = compressed.data();
  z.avail_out = compressed.size();
  assert(deflate(&z, Z_FINISH) == Z_STREAM_END);
  compressed.resize(z.total_out);
  assert(deflateEnd(&z) == Z_OK);
  if (fault == "negative_read")
    compressed.assign(32, 0x55);
  Presonus::FirmwareBundle bundle;
  presonus::application::ResourceAccess::set(bundle, compressed,
                                             fault != "open");
  presonus::noaa::SpiPacketState state({}, 0, 0, 8);
  Presonus::NOAA::TCardSPI spi(state);
  Transport transport(services, fault, after);
  presonus::noaa::SpiServiceAccess::bind(spi, transport, 42, {}, 0);
  assert(!presonus::noaa::SpiServiceAccess::singleton());
  presonus::noaa::SpiServiceAccess::singleton(&spi);
  unsigned result;
  std::vector<unsigned> response;
  {
    Presonus::NOAA::TCardFPGAUpdater updater(&listener, &bundle);
    services.updater = &updater;
    updater.setPortableServices(services);
    updater.cancelPortableUpdate(cancelled);
    if (mode == "update")
      result = updater.update();
    else {
      std::array<unsigned char, 260> command;
      for (unsigned i = 0; i < command.size(); ++i)
        command[i] = (i * 17 + 3) & 255;
      result =
          updater.waitFirmwareCommand(null ? nullptr : command.data(), length,
                                      message == 2 ? ""
                                      : message    ? "wait"
                                                   : nullptr,
                                      timeout);
    }
    const auto &s = updater.portableState();
    response = {s.command, s.infoWords[0], s.status};
    // Independent epoch linkage check: update's first emitted progress must
    // use the just-recorded100ms epoch, so its fraction is exactly zero.
    if (mode == "update")
      assert(!listener.fractions.empty() && listener.fractions.front() == 0.f);
  }
  assert(state.receivers.count() == 0);
  presonus::noaa::SpiServiceAccess::singleton(nullptr);
  presonus::noaa::SpiServiceAccess::bind(spi, transport, -1, {}, 0);
  std::cout << "{\"return\":" << result << ",\"packets\":";
  strings(transport.packets);
  std::cout << ",\"messages\":";
  strings(listener.messages);
  std::cout << ",\"debug\":";
  strings(services.debug);
  std::cout << ",\"sleeps\":";
  numbers(services.sleeps);
  std::cout << ",\"state\":";
  numbers(response);
  std::cout << ",\"opens\":" << (fault == "open" ? 1 : opens)
            << ",\"closes\":" << closes << ",\"reads\":" << reads
            << ",\"pumps\":";
  numbers(services.pumps);
  std::cout << ",\"notices\":" << services.notices << "}\n";
  // Original block timeout intentionally leaves its stream open; verify that
  // observation, then perform fixture-only cleanup after emitting the result.
  if (mode == "update" && result == 2000 && opens && !closes)
    bundle.closeBinImage();
}
