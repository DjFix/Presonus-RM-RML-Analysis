#include "core/public/corememstream.h"
#include "presonus/uc/DiceEndPoint.hpp"
#include "presonus/uc/DicePacketQueue.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Presonus::UC;
namespace {
bool traceEnabled = true;
void *watched = nullptr;
unsigned watchedDeletes = 0;
std::string hex(const void *p, unsigned n) {
  static const char digits[] = "0123456789abcdef";
  const auto *b = static_cast<const unsigned char *>(p);
  std::string s;
  for (unsigned i = 0; i < n; ++i) {
    s += digits[b[i] >> 4];
    s += digits[b[i] & 15];
  }
  return s.empty() ? "-" : s;
}
std::vector<unsigned char> unhex(std::string s) {
  std::vector<unsigned char> b;
  if (s == "-")
    return b;
  for (unsigned i = 0; i < s.size(); i += 2)
    b.push_back(std::stoi(s.substr(i, 2), nullptr, 16));
  return b;
}
void emit(const std::string &s) {
  if (traceEnabled)
    std::cout << s << std::endl;
}
class RecordingStream : public Core::IO::MemoryStream {
  bool negative_, injected_ = false;

public:
  RecordingStream(std::vector<unsigned char> &data, bool negative)
      : MemoryStream(data.data(), data.size()), negative_(negative) {}
  int readBytes(void *p, int n) override {
    int result;
    if (negative_ && !injected_) {
      injected_ = true;
      std::memset(p, 0x5a, 256);
      result = -1;
    } else
      result = MemoryStream::readBytes(p, n);
    emit("S " + std::to_string(n) + " " + std::to_string(result) + " " +
         hex(p, result < 0 ? 256 : result));
    return result;
  }
  Core::int64 setPosition(Core::int64 p, int mode) override {
    injected_ = false;
    auto result = MemoryStream::setPosition(p, mode);
    emit("K " + std::to_string(p) + " " + std::to_string(mode) + " " +
         std::to_string(result));
    return result;
  }
};
class RecordingEndpoint : public DiceEndPoint {
public:
  using DiceEndPoint::DiceEndPoint;
  std::uint32_t read(void *p, int n) override {
    auto result = DataChannel::read(p, n);
    emit("E " + std::to_string(n) + " " + std::to_string(result) + " " +
         hex(p, 256));
    return result;
  }
};
DicePacketQueue *incoming;
std::string direction(PacketQueue *p) { return p == incoming ? "I" : "O"; }
} // namespace
void operator delete(void *p) noexcept {
  if (p == watched) {
    ++watchedDeletes;
    watched = nullptr;
  }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
extern "C" {
void endpointD1(DiceEndPoint *) asm("_ZN8Presonus2UC12DiceEndPointD1Ev");
void channelD1(DataChannel *) asm("_ZN8Presonus2UC11DataChannelD1Ev");
void endpointC1(DiceEndPoint *, DicePacketQueue &, DicePacketQueue &) asm(
    "_ZN8Presonus2UC12DiceEndPointC1ERNS0_15DicePacketQueueES3_");
void endpointC2(DiceEndPoint *, DicePacketQueue &, DicePacketQueue &) asm(
    "_ZN8Presonus2UC12DiceEndPointC2ERNS0_15DicePacketQueueES3_");
int real_write(PacketQueue *, const char *,
               int) asm("__real__ZN8Presonus2UC11PacketQueue5writeEPKci");
int wrap_write(PacketQueue *, const char *,
               int) asm("__wrap__ZN8Presonus2UC11PacketQueue5writeEPKci");
int wrap_write(PacketQueue *q, const char *p, int n) {
  int r = real_write(q, p, n);
  emit("W " + std::to_string(n) + " " + hex(p, n) + " " + std::to_string(r));
  return r;
}
bool real_peak(DicePacketQueue *, unsigned char *, unsigned char &) asm(
    "__real__ZN8Presonus2UC15DicePacketQueue8peakMIDIEPhRh");
bool wrap_peak(DicePacketQueue *, unsigned char *, unsigned char &) asm(
    "__wrap__ZN8Presonus2UC15DicePacketQueue8peakMIDIEPhRh");
bool wrap_peak(DicePacketQueue *q, unsigned char *p, unsigned char &n) {
  auto before = n;
  bool r = real_peak(q, p, n);
  emit("P " + std::to_string(before) + " " + std::to_string(r) + " " +
       std::to_string(n) + " " + hex(p, n));
  return r;
}
bool real_mread(DicePacketQueue *, unsigned char *, unsigned char &) asm(
    "__real__ZN8Presonus2UC15DicePacketQueue8readMIDIEPhRh");
bool wrap_mread(DicePacketQueue *, unsigned char *, unsigned char &) asm(
    "__wrap__ZN8Presonus2UC15DicePacketQueue8readMIDIEPhRh");
bool wrap_mread(DicePacketQueue *q, unsigned char *p, unsigned char &n) {
  auto before = n;
  bool r = real_mread(q, p, n);
  emit("R " + std::to_string(before) + " " + std::to_string(r) + " " +
       std::to_string(n) + " " + hex(p, n));
  return r;
}
bool real_mwrite(DicePacketQueue *, const unsigned char *) asm(
    "__real__ZN8Presonus2UC15DicePacketQueue9writeMIDIEPKh");
bool wrap_mwrite(DicePacketQueue *, const unsigned char *) asm(
    "__wrap__ZN8Presonus2UC15DicePacketQueue9writeMIDIEPKh");
bool wrap_mwrite(DicePacketQueue *q, const unsigned char *p) {
  unsigned n = 0;
  while (n < 255 && p[n] != 0xf7)
    ++n;
  if (n < 255)
    ++n;
  bool r = real_mwrite(q, p);
  emit("M " + hex(p, n) + " " + std::to_string(r));
  return r;
}
void real_flush(PacketQueue *) asm(
    "__real__ZN8Presonus2UC11PacketQueue5flushEv");
void wrap_flush(PacketQueue *) asm(
    "__wrap__ZN8Presonus2UC11PacketQueue5flushEv");
void wrap_flush(PacketQueue *q) {
  auto before = q->getTotalBytes();
  real_flush(q);
  emit("F " + direction(q) + " " + std::to_string(before) + " " +
       std::to_string(q->getTotalBytes()));
}
}
int main(int argc, char **argv) {
  try {
    if (argc < 2)
      return 2;
    std::string mode = argv[1];
    DicePacketQueue in, out;
    incoming = &in;
    if (mode == "lifecycle") {
      traceEnabled = false;
      const char payload[] = "queues survive object destruction";
      in.write(payload, sizeof(payload));
      out.write(payload, sizeof(payload));
      {
        DiceEndPoint endpoint(in, out);
        DataChannel &base = endpoint;
        char b[2];
        if (base.read(b, 2) != 2)
          throw std::runtime_error("base dispatch");
      }
      if (in.getTotalBytes() != sizeof(payload) - 2 ||
          out.getTotalBytes() != sizeof(payload))
        throw std::runtime_error("D1 owns queues");
      // Dead-object vptr bytes are not a portable C++ guarantee. Optimizers
      // may eliminate destructor table stores and sanitizers may clear them.
      // Native D1 table writes are checked in the independent ARM oracle.
      // Here verify real original-scoped lifecycle calls, provider byte/queue
      // survival, and actual D0 deallocation without inspecting dead storage.
      auto queuesSurvive = [&] {
        std::array<char, sizeof(payload)> buffer{};
        if (in.getTotalBytes() != sizeof(payload) - 2 ||
            out.getTotalBytes() != sizeof(payload) ||
            in.peek(buffer.data(), sizeof(payload)) != sizeof(payload) - 2 ||
            std::memcmp(buffer.data(), payload + 2, sizeof(payload) - 2) != 0 ||
            out.peek(buffer.data(), sizeof(payload)) != sizeof(payload) ||
            std::memcmp(buffer.data(), payload, sizeof(payload)) != 0)
          throw std::runtime_error("lifecycle modified borrowed queue bytes");
      };
      queuesSurvive();
      for (auto constructor : {endpointC1, endpointC2}) {
        alignas(DiceEndPoint) unsigned char storage[sizeof(DiceEndPoint)];
        auto *endpoint = reinterpret_cast<DiceEndPoint *>(storage);
        constructor(endpoint, in, out);
        if (!endpoint->isReadable(0))
          throw std::runtime_error("explicit constructor queue binding");
        endpointD1(endpoint);
        queuesSurvive();
      }
      watched = new DiceEndPoint(in, out);
      DataChannel *base = static_cast<DiceEndPoint *>(watched);
      delete base;
      if (watchedDeletes != 1 || watched != nullptr)
        throw std::runtime_error("D0 delete/queues");
      queuesSurvive();
      alignas(DataChannel) unsigned char channelStorage[sizeof(DataChannel)];
      auto *channel = new (channelStorage) DataChannel(in, out);
      channelD1(channel);
      queuesSurvive();
      std::cout << "actual virtual dispatch, both non-owning D1 lifecycles, "
                   "real D0 deallocation and surviving queues passed\n";
      return 0;
    }
    if (argc != 5)
      return 2;
    auto data = unhex(argv[2]);
    bool negative = std::stoi(argv[3]);
    int preload = std::stoi(argv[4]);
    traceEnabled = false;
    if (preload) {
      auto *p = DicePacketQueue::getFactory().createPacket();
      p->length = preload == 1 ? 0 : -1;
      out.prependPacket(p);
    }
    RecordingStream stream(data, negative);
    traceEnabled = true;
    if (mode == "run") {
      RecordingEndpoint endpoint(in, out);
      endpoint.test(stream);
    } else if (mode == "provider") {
      DataChannel channel(in, out);
      std::string line;
      while (std::getline(std::cin, line)) {
        std::istringstream input(line);
        char op;
        input >> op;
        int n = 0;
        std::string h;
        std::array<unsigned char, 256> b{};
        if (op == 'S') {
          input >> n;
          stream.readBytes(b.data(), n);
        } else if (op == 'K')
          stream.setPosition(0, Core::IO::kSeekSet);
        else if (op == 'W') {
          input >> n >> h;
          auto v = unhex(h);
          std::copy(v.begin(), v.end(), b.begin());
          wrap_write(&out, reinterpret_cast<char *>(b.data()), n);
        } else if (op == 'P' || op == 'R') {
          input >> n;
          auto len = static_cast<unsigned char>(n);
          if (op == 'P')
            wrap_peak(&out, b.data(), len);
          else
            wrap_mread(&out, b.data(), len);
        } else if (op == 'M') {
          input >> h;
          auto v = unhex(h);
          std::copy(v.begin(), v.end(), b.begin());
          wrap_mwrite(&in, b.data());
        } else if (op == 'E') {
          input >> n;
          b.fill(0xfe);
          auto result = channel.read(b.data(), n);
          emit("E " + std::to_string(n) + " " + std::to_string(result) + " " +
               hex(b.data(), 256));
        } else if (op == 'F') {
          input >> h;
          wrap_flush(h == "I" ? &in : &out);
        } else
          throw std::runtime_error("provider opcode");
      }
    } else
      return 2;
    traceEnabled = false;
    if (in.getTotalBytes() || out.getTotalBytes())
      throw std::runtime_error("unflushed queues");
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
