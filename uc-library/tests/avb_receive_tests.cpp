#include "presonus/avb/protocol.hpp"
#include "presonus/avb/receive_services.hpp"
#include "presonus/dice/sysex.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <zlib.h>

using Presonus::AVB::AvbListener;
using Presonus::AVB::AvbManagerBase;
using Presonus::AVB::AvbTalker;

static void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}
template <std::size_t N>
static std::array<unsigned char, N> bytes(const std::string &text) {
  require(text.size() == N * 2, "hex buffer size");
  std::array<unsigned char, N> result{};
  for (std::size_t index = 0; index < N; ++index)
    result[index] = static_cast<unsigned char>(
        std::stoul(text.substr(index * 2, 2), nullptr, 16));
  return result;
}
static int signedWord(std::uint32_t word) {
  int result;
  std::memcpy(&result, &word, sizeof result);
  return result;
}

struct Trace {
  AvbManagerBase *manager = nullptr;
  presonus::avb::ReceiveContext *context = nullptr;
  std::vector<AvbListener *> listeners;
  std::vector<AvbTalker *> talkers;
  unsigned helperCalls = 0, noticeCalls = 0, matchedIndex = 0;
  std::uint32_t helperStatus = 0, callbackReturn = 0;
  std::array<unsigned char, 64> decoded{};
  std::array<unsigned char, 3> arguments{};
  char update = '-';
  bool updateResult = false, mutate = false;
  std::string order;
};
static Trace *trace = nullptr;

template <typename T>
static unsigned indexOf(const std::vector<T *> &collection, T *stream) {
  for (unsigned index = 0; index < collection.size(); ++index)
    if (collection[index] == stream)
      return index;
  throw std::runtime_error("unknown stream identity");
}

extern "C" int __real__ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi(
    AvbManagerBase *, unsigned char *, const unsigned char *, int);
extern "C" int __wrap__ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi(
    AvbManagerBase *manager, unsigned char *destination,
    const unsigned char *source, int length) {
  const int result =
      __real__ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi(
          manager, destination, source, length);
  if (trace) {
    require(trace->manager == manager, "unpack original this");
    ++trace->helperCalls;
    trace->helperStatus = static_cast<std::uint32_t>(result);
    std::copy(destination, destination + 64, trace->decoded.begin());
    trace->order += 'H';
  }
  return result;
}

extern "C" bool __real__ZN8Presonus3AVB11AvbListener6updateEhhh(AvbListener *,
                                                                unsigned char,
                                                                unsigned char,
                                                                unsigned char);
extern "C" bool __wrap__ZN8Presonus3AVB11AvbListener6updateEhhh(
    AvbListener *stream, unsigned char first, unsigned char second,
    unsigned char third) {
  const bool result = __real__ZN8Presonus3AVB11AvbListener6updateEhhh(
      stream, first, second, third);
  if (trace) {
    require(trace->update == '-', "duplicate update");
    trace->update = 'L';
    trace->matchedIndex = indexOf(trace->listeners, stream);
    trace->arguments = {first, second, third};
    trace->updateResult = result;
    trace->order += 'U';
  }
  return result;
}

extern "C" bool __real__ZN8Presonus3AVB9AvbTalker6updateEhh(AvbTalker *,
                                                            unsigned char,
                                                            unsigned char);
extern "C" bool __wrap__ZN8Presonus3AVB9AvbTalker6updateEhh(
    AvbTalker *stream, unsigned char first, unsigned char second) {
  const bool result =
      __real__ZN8Presonus3AVB9AvbTalker6updateEhh(stream, first, second);
  if (trace) {
    require(trace->update == '-', "duplicate update");
    trace->update = 'T';
    trace->matchedIndex = indexOf(trace->talkers, stream);
    trace->arguments = {first, second, 0};
    trace->updateResult = result;
    trace->order += 'U';
  }
  return result;
}

class Notices : public presonus::avb::NoticeSink {
  std::uint32_t common(Presonus::AVB::AvbNoticeListener *identity, char type,
                       unsigned index) {
    require(reinterpret_cast<std::uintptr_t>(identity) == 0x10002000,
            "notice original this");
    require(trace && trace->update == type && trace->matchedIndex == index,
            "notice stream identity/order");
    ++trace->noticeCalls;
    trace->order += 'N';
    if (trace->mutate) {
      trace->context->command = 0x6e;
      trace->context->status = 0x9a;
      trace->context->processingWord = 0;
      trace->context->listeners.removeAll();
      trace->context->talkers.removeAll();
    }
    return trace->callbackReturn;
  }

public:
  std::uint32_t listenerChanged(Presonus::AVB::AvbNoticeListener *identity,
                                AvbListener *stream) override {
    return common(identity, 'L', indexOf(trace->listeners, stream));
  }
  std::uint32_t talkerChanged(Presonus::AVB::AvbNoticeListener *identity,
                              AvbTalker *stream) override {
    return common(identity, 'T', indexOf(trace->talkers, stream));
  }
};

template <typename T> struct Slot {
  alignas(T) std::array<unsigned char, sizeof(T)> storage{};
  T *object = nullptr;
  ~Slot() {
    if (object)
      object->~T();
  }
};

int main(int argc, char **argv) {
  try {
    require(argc == 2, "receive fixture required");
    gzFile input = gzopen(argv[1], "rb");
    require(input != nullptr, "fixture open");
    std::array<char, 2048> line{};
    unsigned long cases = 0;
    while (gzgets(input, line.data(), line.size())) {
      std::istringstream row(line.data());
      std::uint32_t gate, initialCommand, initialStatus, prefix, length,
          listenerCount, talkerCount, callbackReturn, mutate, expectedGate,
          expectedCommand, expectedStatus, expectedListeners, expectedTalkers,
          helperCalls, helperStatus, matchedIndex, first, second, third,
          noticeCalls, rawOriginalReturn;
      std::string listenerIdsText, talkerIdsText, packetText, scratchText,
          decodedText;
      char update;
      row >> std::hex >> gate >> initialCommand >> initialStatus >> prefix >>
          length >> listenerCount >> talkerCount >> listenerIdsText >>
          talkerIdsText >> callbackReturn >> mutate >> packetText >>
          scratchText >> expectedGate >> expectedCommand >> expectedStatus >>
          expectedListeners >> expectedTalkers >> helperCalls >> helperStatus >>
          decodedText >> update >> matchedIndex >> first >> second >> third >>
          noticeCalls >> rawOriginalReturn;
      require(!row.fail() && listenerCount <= 4 && talkerCount <= 4,
              "malformed fixture");
      const auto listenerIds = bytes<4>(listenerIdsText);
      const auto talkerIds = bytes<4>(talkerIdsText);
      Presonus::DICE::SysexPacket packet;
      packet.bytes = bytes<256>(packetText);
      packet.length = static_cast<unsigned char>(length);
      const auto packetBefore = packet.bytes;
      presonus::avb::ReceiveContext context;
      context.processingWord = signedWord(gate);
      context.command = static_cast<unsigned char>(initialCommand);
      context.status = static_cast<unsigned char>(initialStatus);
      context.prefixBeforeData = static_cast<unsigned char>(prefix);
      context.initialScratch = bytes<64>(scratchText);
      const auto scratchBefore = context.initialScratch;
      context.noticeIdentity =
          reinterpret_cast<Presonus::AVB::AvbNoticeListener *>(0x10002000ULL);
      Notices notices;
      context.notices = &notices;
      std::array<Slot<AvbListener>, 4> listeners;
      std::array<Slot<AvbTalker>, 4> talkers;
      std::array<std::array<unsigned char, sizeof(AvbListener)>, 4>
          listenerBefore{};
      std::array<std::array<unsigned char, sizeof(AvbTalker)>, 4>
          talkerBefore{};
      for (unsigned index = 0; index < listenerCount; ++index) {
        auto &slot = listeners[index];
        slot.storage.fill(0xa5);
        slot.object = new (slot.storage.data()) AvbListener(
            listenerIds[index],
            0x1122334455660000ULL |
                (static_cast<unsigned long long>(listenerIds[index]) << 8) |
                index,
            static_cast<unsigned short>(0x1000 + index),
            signedWord(0x80000000U | index));
        context.listeners.append(slot.object);
        listenerBefore[index] = slot.storage;
      }
      for (unsigned index = 0; index < talkerCount; ++index) {
        auto &slot = talkers[index];
        slot.storage.fill(0xa5);
        slot.object = new (slot.storage.data())
            AvbTalker(talkerIds[index], signedWord(0x7fffffffU - index));
        context.talkers.append(slot.object);
        talkerBefore[index] = slot.storage;
      }
      AvbManagerBase manager;
      manager.bindReceiveContext(context);
      Trace current;
      current.manager = &manager;
      current.context = &context;
      for (auto *item : context.listeners)
        current.listeners.push_back(item);
      for (auto *item : context.talkers)
        current.talkers.push_back(item);
      current.callbackReturn = callbackReturn;
      current.mutate = mutate != 0;
      current.decoded = context.initialScratch;
      trace = &current;
      manager.receive(packet);
      trace = nullptr;
      require(static_cast<std::uint32_t>(context.processingWord) ==
                      expectedGate &&
                  context.command == expectedCommand &&
                  context.status == expectedStatus &&
                  context.listeners.count() == expectedListeners &&
                  context.talkers.count() == expectedTalkers,
              "receive state");
      require(current.helperCalls == helperCalls &&
                  current.helperStatus == helperStatus &&
                  current.decoded == bytes<64>(decodedText),
              "helper exact status/frame");
      require(current.update == update &&
                  current.matchedIndex == matchedIndex &&
                  current.arguments ==
                      std::array<unsigned char, 3>{
                          static_cast<unsigned char>(first),
                          static_cast<unsigned char>(second),
                          static_cast<unsigned char>(third)},
              "decoded update arguments");
      require(current.updateResult == (update != '-') &&
                  current.noticeCalls == noticeCalls,
              "update return/notice count");
      const std::string expectedOrder = std::string(helperCalls ? "H" : "") +
                                        (update != '-' ? "U" : "") +
                                        (noticeCalls ? "N" : "");
      require(current.order == expectedOrder, "exact call ordering");
      require(context.initialScratch == scratchBefore &&
                  context.prefixBeforeData == prefix &&
                  packet.bytes == packetBefore && packet.length == length,
              "input/seed changed");
      for (unsigned index = 0; index < listenerCount; ++index)
        require(listeners[index].storage == listenerBefore[index],
                "listener state changed");
      for (unsigned index = 0; index < talkerCount; ++index)
        require(talkers[index].storage == talkerBefore[index],
                "talker state changed");
      (void)rawOriginalReturn; // Original return declaration is explicitly
                               // pending.
      ++cases;
    }
    require(gzclose(input) == Z_OK, "fixture close");
    std::cout << "PASS " << cases
              << " original ARM receive state/frame/ordered-call fixtures\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
