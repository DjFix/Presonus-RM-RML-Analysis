#include "core/portable/corepersistence.h"
#include "core/portable/corezipstream.h"
#include "core/public/corememstream.h"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using Core::IO::Buffer;
using Core::IO::MemoryStream;
using Core::IO::Stream;
using Core::Portable::Archiver;
using Core::Portable::Attributes;
using Presonus::UC::MessageAttributes;
using Presonus::UC::MutableMessageEvent;
using Access = presonus::uc::MutableMessageEventPortAccess;
namespace test {
bool capture = false;
unsigned depth = 0;
int status = 1;
MutableMessageEvent *object = nullptr;
std::vector<std::string> events;
std::map<void *, unsigned> actualFreeCounts;
void *watched = nullptr;
unsigned transfers = 0, donorInvalidations = 0, forwardedStorageFrees = 0;
void require(bool b, const char *m) {
  if (!b)
    throw std::runtime_error(m);
}
bool outer() { return capture && depth == 0; }
void event(std::string e) {
  if (outer())
    events.push_back(e);
}
std::string trace() {
  std::string s;
  for (auto &e : events) {
    if (!s.empty())
      s += ',';
    s += e;
  }
  return s;
}
struct Guard {
  Guard() { ++depth; }
  ~Guard() { --depth; }
};
} // namespace test
extern "C" void __real_core_free(void *);
extern "C" void __wrap_core_free(void *p) {
  if (p) {
    ++test::actualFreeCounts[p];
    if (p == test::watched)
      ++test::forwardedStorageFrees;
  }
  __real_core_free(p);
}
extern "C" void __real__ZN4Core2IO6BufferC1EPvjb(Buffer *, void *, unsigned,
                                                 bool);
extern "C" void __wrap__ZN4Core2IO6BufferC1EPvjb(Buffer *self, void *p,
                                                 unsigned n, bool copy) {
  if (test::outer()) {
    test::require(self == &Access::buffer(*test::object) && p == nullptr &&
                      n == 0 && copy,
                  "initial owned Buffer mismatch");
    auto &e = Access::event(*test::object);
    test::require(e.header.type == 0x4a4d && e.header.reserved04 == 24 &&
                      e.header.routeA == 0 && e.header.routeB == 0 &&
                      e.data == nullptr && e.sizeBits == 0,
                  "event not initialized before Buffer");
  }
  test::event("ctor");
  test::Guard g;
  __real__ZN4Core2IO6BufferC1EPvjb(self, p, n, copy);
}
extern "C" bool __real__ZN4Core2IO6Buffer6resizeEj(Buffer *, unsigned);
extern "C" bool __wrap__ZN4Core2IO6Buffer6resizeEj(Buffer *self, unsigned n) {
  bool top = test::outer();
  if (top)
    test::require(n == 0 && self == &Access::buffer(*test::object),
                  "resize boundary mismatch");
  test::event("resize:" + std::to_string(n));
  test::Guard g;
  bool result = __real__ZN4Core2IO6Buffer6resizeEj(self, n);
  return top ? bool(test::status) : result;
}
extern "C" Buffer &__real__ZN4Core2IO6Buffer4takeERS1_(Buffer *, Buffer &);
extern "C" Buffer &__wrap__ZN4Core2IO6Buffer4takeERS1_(Buffer *self,
                                                       Buffer &other) {
  bool top = test::outer();
  void *pointer = other.getAddress();
  auto size = other.getSize();
  if (top)
    test::require(self == &Access::buffer(*test::object) && self->isNull(),
                  "destination not cleared before take");
  test::event("take");
  test::Guard g;
  auto &result = __real__ZN4Core2IO6Buffer4takeERS1_(self, other);
  if (top) {
    test::require(self->getAddress() == pointer && self->getSize() == size &&
                      other.isNull() && other.getSize() == 0,
                  "actual transfer/source invalidation mismatch");
    ++test::transfers;
    ++test::donorInvalidations;
  }
  return result;
}
extern "C" void __real__ZN4Core2IO12MemoryStreamC1Ej(MemoryStream *, unsigned);
extern "C" void __wrap__ZN4Core2IO12MemoryStreamC1Ej(MemoryStream *self,
                                                     unsigned n) {
  test::event("heavy:" + std::to_string(n));
  test::Guard g;
  __real__ZN4Core2IO12MemoryStreamC1Ej(self, n);
}
extern "C" const Buffer &
__real__ZNK4Core2IO12MemoryStream9getBufferEv(const MemoryStream *);
extern "C" const Buffer &
__wrap__ZNK4Core2IO12MemoryStream9getBufferEv(const MemoryStream *self) {
  test::event("buffer");
  test::Guard g;
  return __real__ZNK4Core2IO12MemoryStream9getBufferEv(self);
}
extern "C" unsigned
__real__ZNK4Core2IO12MemoryStream15getBytesWrittenEv(const MemoryStream *);
extern "C" unsigned
__wrap__ZNK4Core2IO12MemoryStream15getBytesWrittenEv(const MemoryStream *self) {
  test::event("written");
  test::Guard g;
  return __real__ZNK4Core2IO12MemoryStream15getBytesWrittenEv(self);
}
extern "C" bool
__real__ZN4Core2IO12MemoryStream14allocateMemoryEjb(MemoryStream *, unsigned,
                                                    bool);
extern "C" bool
__wrap__ZN4Core2IO12MemoryStream14allocateMemoryEjb(MemoryStream *self,
                                                    unsigned n, bool zero) {
  bool top = test::outer();
  if (top)
    test::require(n > 0 && !zero, "allocation hint changed");
  test::event("allocate:" + std::to_string(n));
  test::Guard g;
  bool result =
      __real__ZN4Core2IO12MemoryStream14allocateMemoryEjb(self, n, zero);
  return top ? bool(test::status) : result;
}
extern "C" void
__real__ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi(
    Archiver *, Stream *, Archiver::Format, int);
extern "C" void
__wrap__ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi(
    Archiver *self, Stream *s, Archiver::Format f, int flags) {
  if (test::outer()) {
    const auto &e = Access::event(*test::object);
    test::require(e.header.routeA == 0x11223344 &&
                      e.header.routeB == 0xaabbccdd,
                  "metadata not copied before archive construction");
  }
  test::event("archive:" + std::to_string(f) + ":" + std::to_string(flags));
  test::Guard g;
  __real__ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi(self, s, f,
                                                                   flags);
}
extern "C" bool
__real__ZN4Core8Portable8Archiver4saveERKNS0_10AttributesE(Archiver *,
                                                           const Attributes &);
extern "C" bool __wrap__ZN4Core8Portable8Archiver4saveERKNS0_10AttributesE(
    Archiver *self, const Attributes &a) {
  bool top = test::outer();
  test::event("save");
  test::Guard g;
  bool result =
      __real__ZN4Core8Portable8Archiver4saveERKNS0_10AttributesE(self, a);
  return top ? bool(test::status) : result;
}
extern "C" bool
__real__ZN4Core8Portable22ThreadAwareCompression3zipERNS_2IO6StreamEPKvii(
    Stream &, const void *, int, int);
extern "C" bool
__wrap__ZN4Core8Portable22ThreadAwareCompression3zipERNS_2IO6StreamEPKvii(
    Stream &s, const void *p, int n, int window) {
  bool top = test::outer();
  if (top)
    test::require(window == 15, "zip window changed");
  test::event("zip:" + std::to_string(window));
  test::Guard g;
  bool result =
      __real__ZN4Core8Portable22ThreadAwareCompression3zipERNS_2IO6StreamEPKvii(
          s, p, n, window);
  return top ? bool(test::status) : result;
}
extern "C" void __real__ZN4Core2IO6BufferD1Ev(Buffer *);
extern "C" void __real__ZN4Core2IO6BufferD2Ev(Buffer *);
extern "C" void __wrap__ZN4Core2IO6BufferD1Ev(Buffer *self) {
  test::event("cleanup");
  test::Guard g;
  __real__ZN4Core2IO6BufferD1Ev(self);
}
extern "C" void __wrap__ZN4Core2IO6BufferD2Ev(Buffer *self) {
  test::event("cleanup");
  test::Guard g;
  __real__ZN4Core2IO6BufferD2Ev(self);
}
int main(int argc, char **argv) {
  try {
    test::require(argc == 2, "fixture argument required");
    std::ifstream file(argv[1]);
    test::require(bool(file), "fixture missing");
    std::string line;
    unsigned cases = 0, cleanupCases = 0;
    while (std::getline(file, line)) {
      std::istringstream row(line);
      std::string role, action, expected;
      std::uint32_t tag;
      int n, hint, status;
      row >> role >> action >> tag >> n >> hint >> status >> expected;
      test::require(bool(row), "bad fixture");
      Presonus::UC::MessageEvent seed{};
      seed.header.routeA = 0x11223344;
      seed.header.routeB = 0xaabbccdd;
      MessageAttributes attributes(seed);
      attributes.setID("native-owned");
      attributes.setSource("source");
      attributes.setURL("url");
      MemoryStream input(64);
      std::vector<unsigned char> bytes(n, 'q');
      if (n)
        input.writeBytes(bytes.data(), n);
      auto originalCount = input.getBytesWritten();
      void *originalPointer =
          const_cast<void *>(input.getBuffer().getAddress());
      alignas(MutableMessageEvent) unsigned char
          storage[sizeof(MutableMessageEvent)];
      test::object = reinterpret_cast<MutableMessageEvent *>(storage);
      bool constructor = action[0] == 'C';
      if (!constructor)
        new (storage) MutableMessageEvent();
      test::events.clear();
      test::status = status;
      test::capture = true;
      if (action == "C1" || action == "C2")
        new (storage) MutableMessageEvent();
      else if (constructor)
        new (storage)
            MutableMessageEvent(attributes, static_cast<int>(tag), hint);
      else if (action == "A")
        test::require(&test::object->assign(attributes, static_cast<int>(tag),
                                            hint) == test::object,
                      "attrs assign self projection changed");
      else if (action == "S")
        test::require(&test::object->assign(input, static_cast<int>(tag)) ==
                          test::object,
                      "stream assign self projection changed");
      else
        test::object->takeData(input, status != 0);
      test::capture = false;
      test::require(test::trace() == expected,
                    ("app boundary trace mismatch: " + test::trace() +
                     " expected " + expected)
                        .c_str());
      auto &event = Access::event(*test::object);
      const auto &buffer = Access::buffer(*test::object);
      test::require(event.data == buffer.getAddress(),
                    "event pointer differs from owned buffer");
      if (!constructor || action == "C1a" || action == "C2a") {
        bool zip =
            action == "T" ? status != 0 : (tag == 0x5a42 || tag == 0x5a4d);
        if (action == "S" || action == "T") {
          test::require(input.getBytesWritten() == originalCount,
                        "donor count changed");
          if (zip) {
            test::require(input.getBuffer().getAddress() == originalPointer,
                          "compressed source stolen");
            if (n)
              test::require(std::memcmp(originalPointer, bytes.data(), n) == 0,
                            "compressed input mutated");
          } else
            test::require(input.getBuffer().isNull(), "donor not invalidated");
          if (!zip) {
            test::require(event.sizeBits == unsigned(n) &&
                              event.data == originalPointer,
                          "uncompressed donor fields changed");
            if (n)
              test::require(std::memcmp(event.data, bytes.data(), n) == 0,
                            "transferred payload changed");
          }
        }
      }
      test::watched = const_cast<void *>(event.data);
      auto prior = test::actualFreeCounts[test::watched];
      test::object->~MutableMessageEvent();
      if (test::watched) {
        test::require(test::actualFreeCounts[test::watched] == prior + 1,
                      "owned Buffer destructor did not forward actual free");
        ++cleanupCases;
      }
      test::watched = nullptr;
      ++cases;
    }
    // Repeated assign releases previous storage before taking another donor.
    MutableMessageEvent target;
    MemoryStream first(64), second(64);
    first.writeBytes("abc", 3);
    second.writeBytes("defgh", 5);
    target.assign(first, 0x4a4d);
    void *old = const_cast<void *>(Access::event(target).data);
    auto frees = test::actualFreeCounts[old];
    target.assign(second, 0x4a4d);
    test::require(test::actualFreeCounts[old] == frees + 1 &&
                      first.getBuffer().isNull() && second.getBuffer().isNull(),
                  "repeat assign ownership failed");
    test::require(Access::event(target).sizeBits == 5 &&
                      std::memcmp(Access::event(target).data, "defgh", 5) == 0,
                  "repeat payload changed");
    unsigned actualSourceCases = 0;
    for (int tag : {0x4a4d, 0x5542, 0x5a4d, 0x5a42}) {
      for (int hint : {-1, 0, 64, 4096}) {
        for (bool withStrings : {false, true}) {
          Presonus::UC::MessageEvent seed{};
          seed.header.routeA = 0x11223344;
          seed.header.routeB = 0xaabbccdd;
          MessageAttributes attrs(seed);
          if (withStrings) {
            attrs.setID("owned-id");
            attrs.setSource("owned-source");
            attrs.setURL("owned-url");
          }
          auto value = std::make_unique<MutableMessageEvent>(attrs, tag, hint);
          const auto &view = Access::event(*value);
          test::require(view.header.type == unsigned(tag) &&
                            view.header.routeA == 0x11223344 &&
                            view.header.routeB == 0xaabbccdd,
                        "serialization metadata changed");
          MessageAttributes parsed(view);
          auto parsedWords =
              presonus::uc::MessageAttributesPortAccess::opaqueState(parsed);
          test::require(
              parsedWords ==
                  presonus::uc::MessageAttributesPortAccess::opaqueState(attrs),
              "metadata roundtrip changed");
          value.reset();
          test::require(parsed.countAttributes() == attrs.countAttributes(),
                        "parsed count changed");
          if (withStrings) {
            test::require(parsed.getID() &&
                              std::strcmp(parsed.getID(), "owned-id") == 0 &&
                              parsed.getSource() &&
                              std::strcmp(parsed.getSource(), "owned-source") ==
                                  0 &&
                              parsed.getURL() &&
                              std::strcmp(parsed.getURL(), "owned-url") == 0,
                          "roundtrip did not preserve independent owned "
                          "strings after payload free");
          }
          ++actualSourceCases;
        }
      }
    }
    // A light donor transfers its borrowing contract, not ownership. The
    // externally owned byte array stays alive through every borrowed use.
    for (bool compress : {false, true}) {
      unsigned char payload[] = {'a', 'b', 'c'};
      auto original = std::vector<unsigned char>(payload, payload + 3);
      const auto before = test::actualFreeCounts[payload];
      {
        MemoryStream light(payload, 3);
        // Light MemoryStream initializes bytesWritten to its full valid size.
        test::require(light.getBytesWritten() == 3,
                      "light donor count differs");
        MutableMessageEvent borrowed;
        borrowed.takeData(light, compress);
        if (!compress)
          test::require(Access::event(borrowed).data == payload &&
                            light.getBuffer().isNull(),
                        "light transfer changed borrowed identity");
        else
          test::require(light.getBuffer().getAddress() == payload,
                        "zip stole light donor");
      }
      test::require(test::actualFreeCounts[payload] == before &&
                        std::memcmp(payload, original.data(), 3) == 0,
                    "borrowed external storage freed or modified");
      ++actualSourceCases;
    }
    std::cout << "PASS original_app_cases=" << cases
              << " actual_transfers=" << test::transfers
              << " donor_invalidations=" << test::donorInvalidations
              << " actual_cleanup_cases=" << cleanupCases
              << " actual_source_cases=" << actualSourceCases
              << " repeated_assignment=true\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
