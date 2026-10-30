#include "core/portable/corepersistence.h"
#include "core/portable/corezipstream.h"
#include "core/public/corememstream.h"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

namespace event_test {
using Core::IO::Buffer;
using Core::IO::MemoryStream;
using Core::IO::Stream;
using Core::Portable::Archiver;
using Core::Portable::AttributeAllocator;
using Core::Portable::Attributes;
using Presonus::UC::MessageAttributes;
using Presonus::UC::MessageEvent;
bool capture = false, expectObject = false;
unsigned providerDepth = 0, allocations = 0, frees = 0;
void *objectMemory = nullptr;
MessageAttributes *object = nullptr;
MessageEvent currentEvent{};
MemoryStream *streamObject = nullptr;
const Buffer *streamBuffer = nullptr;
std::vector<std::string> events;
bool sawLoad = false, unzipResult = false, loadResult = false;
struct Snapshot {
  int count = 0;
  std::array<std::string, 3> values;
  std::array<bool, 3> present{};
};
Snapshot postLoad;
unsigned failedUnzipStillLoaded = 0, failedLoadStatePreserved = 0;
void require(bool result, const char *message) {
  if (!result)
    throw std::runtime_error(message);
}
bool outer() { return capture && providerDepth == 0; }
void event(const std::string &value) {
  if (outer())
    events.push_back(value);
}
std::string trace() {
  std::string value;
  for (const auto &e : events) {
    if (!value.empty())
      value += ',';
    value += e;
  }
  return value;
}
Snapshot snapshot(const Attributes &attrs) {
  Snapshot result;
  result.count = attrs.countAttributes();
  const std::array<const char *, 3> keys{"id", "src", "url"};
  for (unsigned i = 0; i < keys.size(); ++i) {
    const char *value = attrs.getString(keys[i]);
    result.present[i] = value != nullptr;
    if (value)
      result.values[i] = value;
  }
  return result;
}
void compare(const Snapshot &a, const Snapshot &b) {
  require(a.count == b.count && a.present == b.present && a.values == b.values,
          "app rolled back or lost provider partial/owned state");
}
void checkMetadata() {
  const auto bytes =
      presonus::uc::MessageAttributesPortAccess::opaqueState(*object);
  for (unsigned i = 0; i < 4; ++i) {
    require(bytes[i] == static_cast<unsigned char>(currentEvent.header.routeA >>
                                                   (i * 8)),
            "first opaque word not copied before clear");
    require(bytes[i + 4] == static_cast<unsigned char>(
                                currentEvent.header.routeB >> (i * 8)),
            "second opaque word not copied before clear");
  }
}
void recordFree(void *p) {
  if (p && p == objectMemory) {
    ++frees;
    objectMemory = nullptr;
  }
}
bool recognized(std::uint32_t tag) {
  return tag == 0x4a4d || tag == 0x5542 || tag == 0x5a4d || tag == 0x5a42;
}
} // namespace event_test
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  auto *p = __real__Znwm(size);
  if (event_test::expectObject) {
    event_test::expectObject = false;
    event_test::objectMemory = p;
    ++event_test::allocations;
  }
  return p;
}
extern "C" void __wrap__ZdlPv(void *p) {
  event_test::recordFree(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  event_test::recordFree(p);
  __real__ZdlPvm(p, size);
}
extern "C" event_test::AttributeAllocator &
__real__ZN4Core8Portable18AttributeAllocator10getDefaultEv();
extern "C" event_test::AttributeAllocator &
__wrap__ZN4Core8Portable18AttributeAllocator10getDefaultEv() {
  auto &result = __real__ZN4Core8Portable18AttributeAllocator10getDefaultEv();
  event_test::event("allocator");
  return result;
}
extern "C" void
__real__ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE(
    event_test::Attributes *, event_test::AttributeAllocator &);
extern "C" void
__wrap__ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE(
    event_test::Attributes *self, event_test::AttributeAllocator &allocator) {
  using namespace event_test;
  if (outer())
    require(self == objectMemory, "base constructor receiver mismatch");
  event("base_ctor");
  ++providerDepth;
  __real__ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE(self,
                                                                    allocator);
  --providerDepth;
}
extern "C" void
__real__ZN4Core8Portable10Attributes9removeAllEv(event_test::Attributes *);
extern "C" void
__wrap__ZN4Core8Portable10Attributes9removeAllEv(event_test::Attributes *self) {
  using namespace event_test;
  if (outer()) {
    require(self == objectMemory, "clear receiver mismatch");
    checkMetadata();
  }
  event("clear");
  ++providerDepth;
  __real__ZN4Core8Portable10Attributes9removeAllEv(self);
  --providerDepth;
}
extern "C" void
__real__ZN4Core2IO12MemoryStreamC1EPvj(event_test::MemoryStream *, void *,
                                       unsigned);
extern "C" void
__wrap__ZN4Core2IO12MemoryStreamC1EPvj(event_test::MemoryStream *self,
                                       void *data, unsigned size) {
  using namespace event_test;
  const bool track = outer();
  if (track) {
    require(data == currentEvent.data && size == currentEvent.sizeBits,
            "borrowed stream input/size changed");
    event("light");
  }
  ++providerDepth;
  __real__ZN4Core2IO12MemoryStreamC1EPvj(self, data, size);
  --providerDepth;
  if (track) {
    streamObject = self;
    streamBuffer = &self->getBuffer();
  }
}
extern "C" void __real__ZN4Core2IO12MemoryStreamC1Ej(event_test::MemoryStream *,
                                                     unsigned);
extern "C" void
__wrap__ZN4Core2IO12MemoryStreamC1Ej(event_test::MemoryStream *self,
                                     unsigned grow) {
  using namespace event_test;
  const bool track = outer();
  if (track) {
    require(grow == 8192, "owned stream grow changed");
    event("heavy:8192");
  }
  ++providerDepth;
  __real__ZN4Core2IO12MemoryStreamC1Ej(self, grow);
  --providerDepth;
  if (track) {
    streamObject = self;
    streamBuffer = &self->getBuffer();
  }
}
extern "C" bool
__real__ZN4Core8Portable22ThreadAwareCompression5unzipERNS_2IO6StreamEPKvii(
    event_test::Stream &, const void *, int, int);
extern "C" bool
__wrap__ZN4Core8Portable22ThreadAwareCompression5unzipERNS_2IO6StreamEPKvii(
    event_test::Stream &target, const void *data, int size, int window) {
  using namespace event_test;
  const bool track = outer();
  if (track) {
    require(&target == static_cast<Stream *>(streamObject) &&
                data == currentEvent.data &&
                size == static_cast<int>(currentEvent.sizeBits) && window == 15,
            "unzip input/window changed");
    event("unzip:15");
  }
  ++providerDepth;
  const bool result =
      __real__ZN4Core8Portable22ThreadAwareCompression5unzipERNS_2IO6StreamEPKvii(
          target, data, size, window);
  --providerDepth;
  if (track)
    unzipResult = result;
  return result;
}
extern "C" void
__real__ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi(
    event_test::Archiver *, event_test::Stream *, event_test::Archiver::Format,
    int);
extern "C" void
__wrap__ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi(
    event_test::Archiver *self, event_test::Stream *stream,
    event_test::Archiver::Format format, int flags) {
  using namespace event_test;
  if (outer()) {
    const int expected = currentEvent.header.type == 0x5542 ||
                         currentEvent.header.type == 0x5a42;
    require(stream == static_cast<Stream *>(streamObject) &&
                format == expected && flags == 0,
            "archive format/stream/flags changed");
    event("archive:" + std::to_string(format) + ":0");
  }
  ++providerDepth;
  __real__ZN4Core8Portable8ArchiverC1EPNS_2IO6StreamENS1_6FormatEi(
      self, stream, format, flags);
  --providerDepth;
}
extern "C" bool __real__ZN4Core8Portable8Archiver4loadERNS0_10AttributesE(
    event_test::Archiver *, event_test::Attributes &);
extern "C" bool __wrap__ZN4Core8Portable8Archiver4loadERNS0_10AttributesE(
    event_test::Archiver *self, event_test::Attributes &attrs) {
  using namespace event_test;
  const bool track = outer();
  if (track) {
    require(&attrs == objectMemory, "archive destination changed");
    event("load");
  }
  ++providerDepth;
  const bool result =
      __real__ZN4Core8Portable8Archiver4loadERNS0_10AttributesE(self, attrs);
  if (track)
    postLoad = snapshot(attrs);
  --providerDepth;
  if (track) {
    sawLoad = true;
    loadResult = result;
  }
  return result;
}
extern "C" void __real__ZN4Core2IO6BufferD1Ev(event_test::Buffer *);
extern "C" void __real__ZN4Core2IO6BufferD2Ev(event_test::Buffer *);
void bufferCleanup(event_test::Buffer *self) {
  using namespace event_test;
  if (outer() && self == streamBuffer) {
    event("cleanup");
    streamBuffer = nullptr;
  }
}
extern "C" void __wrap__ZN4Core2IO6BufferD1Ev(event_test::Buffer *self) {
  bufferCleanup(self);
  ++event_test::providerDepth;
  __real__ZN4Core2IO6BufferD1Ev(self);
  --event_test::providerDepth;
}
extern "C" void __wrap__ZN4Core2IO6BufferD2Ev(event_test::Buffer *self) {
  bufferCleanup(self);
  ++event_test::providerDepth;
  __real__ZN4Core2IO6BufferD2Ev(self);
  --event_test::providerDepth;
}
namespace event_test {
void beginTarget(const MessageEvent &event) {
  currentEvent = event;
  events.clear();
  streamObject = nullptr;
  streamBuffer = nullptr;
  sawLoad = unzipResult = loadResult = false;
  capture = true;
}
void finishTarget(const std::vector<unsigned char> &before,
                  const std::vector<unsigned char> &after) {
  capture = false;
  require(before == after, "read-only payload was modified");
  checkMetadata();
  if (recognized(currentEvent.header.type)) {
    require(sawLoad, "load skipped after stream/unzip status");
    compare(snapshot(*object), postLoad);
    if ((currentEvent.header.type == 0x5a4d ||
         currentEvent.header.type == 0x5a42) &&
        !unzipResult)
      ++failedUnzipStillLoaded;
    if (!loadResult)
      ++failedLoadStatePreserved;
  } else {
    require(!sawLoad && object->countAttributes() == 0,
            "unknown type accessed payload or failed to clear");
  }
}
std::vector<unsigned char> serialized(bool binary) {
  if (!binary) {
    const std::string json =
        R"({"id":"decoded","src":"source","url":"target","nested":{"n":7}})";
    return {json.begin(), json.end()};
  }
  Attributes attributes(AttributeAllocator::getDefault());
  attributes.set("id", "decoded", false);
  attributes.set("src", "source", false);
  attributes.set("url", "target", false);
  attributes.makeAttributes("nested")->set("n", 7);
  MemoryStream output(8192);
  Archiver archive(&output, Archiver::kUBJSON, 0);
  require(archive.save(attributes), "actual source UBJSON generator failed");
  const auto *bytes =
      static_cast<const unsigned char *>(output.getBuffer().getAddress());
  return {bytes, bytes + output.getBytesWritten()};
}
std::vector<unsigned char> compressed(const std::vector<unsigned char> &bytes) {
  MemoryStream output(8192);
  require(Core::Portable::ThreadAwareCompression::zip(
              output, bytes.data(), static_cast<int>(bytes.size()), 15),
          "actual source zlib generator failed");
  const auto *data =
      static_cast<const unsigned char *>(output.getBuffer().getAddress());
  return {data, data + output.getBytesWritten()};
}
void allocate() {
  expectObject = true;
  object = static_cast<MessageAttributes *>(
      ::operator new(sizeof(MessageAttributes)));
}
void cleanupObject() {
  capture = false;
  delete object;
  object = nullptr;
  require(objectMemory == nullptr, "actual object allocation leaked");
}
} // namespace event_test
int main(int argc, char **argv) {
  using namespace event_test;
  try {
    require(argc == 2, "fixture path required");
    std::ifstream input(argv[1]);
    require(bool(input), "fixture missing");
    std::string role, action, expected;
    std::uint32_t tag, routeA, routeB;
    unsigned payloadKind, simulatedZip, simulatedLoad, cases = 0,
                                                       sourceCases = 0;
    while (input >> role >> action >> tag >> routeA >> routeB >> payloadKind >>
           simulatedZip >> simulatedLoad >> expected) {
      (void)simulatedZip;
      (void)simulatedLoad;
      std::vector<unsigned char> payload(payloadKind ? 31 : 0, 'Z');
      MessageEvent event{};
      event.header.type = tag;
      event.header.routeA = routeA;
      event.header.routeB = routeB;
      event.data = payload.empty() ? nullptr : payload.data();
      event.sizeBits = static_cast<std::uint32_t>(payload.size());
      if (!recognized(tag) && payloadKind) {
        event.data = reinterpret_cast<const void *>(1);
        event.sizeBits = 0xffffffff;
      }
      const auto before = payload;
      allocate();
      if (action == "A") {
        new (object) MessageAttributes("stale");
        object->setSource("stale source");
      }
      beginTarget(event);
      if (action == "A")
        require(&object->assign(event) == object,
                "assign did not return self choice");
      else
        new (object) MessageAttributes(event);
      finishTarget(before, payload);
      require(trace() == expected, "original app/Core boundary order mismatch");
      cleanupObject();
      ++cases;
    }
    require(cases == 1152, "missing original cases");
    for (auto tagValue : {0x4a4dU, 0x5542U, 0x5a4dU, 0x5a42U}) {
      for (unsigned repetition = 0; repetition < 8; ++repetition) {
        auto payload = serialized(tagValue == 0x5542 || tagValue == 0x5a42);
        if (tagValue == 0x5a4d || tagValue == 0x5a42)
          payload = compressed(payload);
        const auto before = payload;
        MessageEvent event{};
        event.header.type = tagValue;
        event.header.routeA = 0x80000000U + repetition;
        event.header.routeB = 0xffffffffU - repetition;
        event.data = payload.data();
        event.sizeBits = static_cast<std::uint32_t>(payload.size());
        allocate();
        new (object) MessageAttributes("stale");
        beginTarget(event);
        require(&object->assign(event) == object, "valid assign self mismatch");
        finishTarget(before, payload);
        require(loadResult && std::strcmp(object->getID(), "decoded") == 0 &&
                    std::strcmp(object->getSource(), "source") == 0 &&
                    std::strcmp(object->getURL(), "target") == 0 &&
                    object->getAttributes("nested")->getInt("n") == 7,
                "actual source JSON/UBJSON/zlib result mismatch");
        payload.assign(payload.size(), 0xdd);
        payload.clear();
        payload.shrink_to_fit();
        require(object->getID() && object->getAttributes("nested") &&
                    std::strcmp(object->getID(), "decoded") == 0 &&
                    object->getAttributes("nested")->getInt("n") == 7,
                "loaded attributes shallow-copied borrowed stream storage");
        cleanupObject();
        ++sourceCases;
      }
    }
    require(allocations == frees, "actual allocation/free imbalance");
    require(failedUnzipStillLoaded > 0 && failedLoadStatePreserved > 0,
            "real failure status/partial-state domains were not exercised");
    std::cout
        << "PASS original_app_cases=" << cases
        << " actual_source_cases=" << sourceCases
        << " actual_object_allocations=" << allocations
        << " actual_forwarded_object_frees=" << frees
        << " failed_unzip_still_loaded=" << failedUnzipStillLoaded
        << " failed_load_state_preserved=" << failedLoadStatePreserved
        << " metadata_order=matched payload_unchanged=true owned_parse=true\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
