#include "presonus/uc/source_default_factory.hpp"
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
using namespace Presonus::UC;
using namespace presonus::uc;
extern "C" void
originalC1(EventFactory *) asm("_ZN8Presonus2UC12EventFactoryC1Ev");
extern "C" void
originalC2(EventFactory *) asm("_ZN8Presonus2UC12EventFactoryC2Ev");
extern "C" void
originalD1(EventFactory *) asm("_ZN8Presonus2UC12EventFactoryD1Ev");
namespace {
int expectedTypes[35] = {20047, 21837, 17473, 17484, 17489, 17745, 20549,
                         20566, 20563, 20557, 20553, 20547, 20562, 20556,
                         19778, 19795, 21571, 19785, 19265, 18002, 17988,
                         18003, 17985, 16975, 19021, 23117, 21826, 23106,
                         17227, 19537, 19538, 17474, 19789, 21331, 21324};
bool captureAllocations = false;
struct Allocation {
  void *address;
  bool freed;
};
Allocation allocations[2048]{};
unsigned allocationCount = 0, freeCount = 0, allocationOrdinal = 0,
         failOrdinal = 0;
void check(bool value) {
  if (!value)
    std::abort();
}
void beforeAllocation() {
  if (captureAllocations && ++allocationOrdinal == failOrdinal)
    throw std::bad_alloc();
}
void allocated(void *p) {
  if (captureAllocations) {
    check(allocationCount < 2048);
    allocations[allocationCount++] = {p, false};
  }
}
void freed(void *p) {
  if (!captureAllocations || !p)
    return;
  for (unsigned n = allocationCount; n > 0; --n)
    if (allocations[n - 1].address == p && !allocations[n - 1].freed) {
      allocations[n - 1].freed = true;
      ++freeCount;
      return;
    }
  check(false);
}
void resetAllocations(unsigned fail = 0) {
  allocationCount = freeCount = allocationOrdinal = 0;
  failOrdinal = fail;
  captureAllocations = true;
}
void assertFreed() {
  captureAllocations = false;
  check(freeCount == allocationCount);
  for (unsigned n = 0; n < allocationCount; ++n)
    check(allocations[n].freed);
}
} // namespace
extern "C" void *__real__Znam(std::size_t);
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znam(std::size_t n) {
  beforeAllocation();
  auto *p = __real__Znam(n);
  allocated(p);
  return p;
}
extern "C" void *__wrap__Znwm(std::size_t n) {
  beforeAllocation();
  auto *p = __real__Znwm(n);
  allocated(p);
  return p;
}
extern "C" void __wrap__ZdaPv(void *p) {
  freed(p);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t n) {
  freed(p);
  __real__ZdaPvm(p, n);
}
extern "C" void __wrap__ZdlPv(void *p) {
  freed(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  freed(p);
  __real__ZdlPvm(p, n);
}
int main() {
  // Actual production object initialization. Ordered entry observations remain
  // a separate instrumented validation gate, with no production tracing hooks.

  {
    EventFactory cold;

    check(DefaultFactorySourceAccess::count(cold) == 35);
  }
  unsigned nativeAllocations = 0, lifecycleCases = 0;
  for (auto construct : {originalC1, originalC2})
    for (unsigned fill : {0u, 165u}) {
      alignas(EventFactory) unsigned char storage[sizeof(EventFactory)];
      std::memset(storage, fill, sizeof(storage));
      auto *factory = reinterpret_cast<EventFactory *>(storage);
      resetAllocations();

      construct(factory);

      check(DefaultFactorySourceAccess::count(*factory) == 35);
      check(DefaultFactorySourceAccess::owner(*factory) != nullptr);
      nativeAllocations = allocationOrdinal;
      for (int type : expectedTypes) {
        auto *item = factory->createType(type);
        check(item && item->getData().type == unsigned(type));
        delete item;
      }
      check(factory->createType(-1) == nullptr &&
            factory->createType(0) == nullptr &&
            factory->createType(65535) == nullptr);
      originalD1(factory);
      assertFreed();
      ++lifecycleCases;
    }
  // Duplicate class registrations are actual map append operations; existing
  // registered provider objects remain shared, live and owned by their statics.
  {
    EventFactory factory;

    factory.addClass<Presonus::UC::PrimitiveEventClassNoMembers<
        Presonus::UC::NoOpEvent, 20047>>();
    factory.addClass<Presonus::UC::UDPMappingEventClass>();
    factory.addClass<Presonus::UC::DiscoveryAliveEventClass>();
    factory.addClass<Presonus::UC::PrimitiveEventClassNoMembers<
        Presonus::UC::DiscoveryLeaveEvent, 17484>>();
    factory.addClass<Presonus::UC::PrimitiveEventClassNoMembers<
        Presonus::UC::DiscoveryQueryEvent, 17489>>();
    factory.addClass<Presonus::UC::ExtensionQueryEventClass>();
    factory.addClass<Presonus::UC::ParamEditEventClass>();
    factory.addClass<Presonus::UC::ParamValueEventClass>();
    factory.addClass<Presonus::UC::ParamStringEventClass>();
    factory.addClass<Presonus::UC::ParamModeEventClass>();
    factory.addClass<Presonus::UC::ParamIncrementEventClass>();
    factory.addClass<Presonus::UC::ParamColorEventClass>();
    factory.addClass<Presonus::UC::ParamRangeEventClass>();
    factory.addClass<Presonus::UC::ParamStringListEventClass>();
    factory.addClass<
        Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>>();
    factory.addClass<
        Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>>();
    factory.addClass<Presonus::UC::TimeCodeEventClass>();
    factory.addClass<Presonus::UC::MusicInputEventClass>();
    factory.addClass<Presonus::UC::PrimitiveEventClassNoMembers<
        Presonus::UC::KeepAliveEvent, 19265>>();
    factory.addClass<Presonus::UC::FileRequestEventClass>();
    factory.addClass<Presonus::UC::FileDataEventClass>();
    factory.addClass<Presonus::UC::FileDataRateEventClass>();
    factory.addClass<Presonus::UC::FileAbortEventClass>();
    factory.addClass<Presonus::UC::BinaryEventClass>();
    factory.addClass<Presonus::UC::DataEventClass<
        Presonus::UC::EncodedMessageEvent<19021>, 19021>>();
    factory.addClass<Presonus::UC::DataEventClass<
        Presonus::UC::EncodedMessageEvent<23117>, 23117>>();
    factory.addClass<Presonus::UC::DataEventClass<
        Presonus::UC::EncodedMessageEvent<21826>, 21826>>();
    factory.addClass<Presonus::UC::DataEventClass<
        Presonus::UC::EncodedMessageEvent<23106>, 23106>>();
    factory.addClass<Presonus::UC::MessageChunkEventClass>();
    factory.addClass<Presonus::UC::DataEventClass<
        Presonus::UC::LoopbackQueryEvent, 19537>>();
    factory.addClass<Presonus::UC::DataEventClass<
        Presonus::UC::LoopbackReplyEvent, 19538>>();
    factory.addClass<Presonus::UC::DebugEventClass>();
    factory.addClass<Presonus::UC::MidiMessageEventClass>();
    factory.addClass<Presonus::UC::MidiShortSysexEventClass>();
    factory.addClass<Presonus::UC::DataEventClass<
        Presonus::UC::MidiLongSysexEvent, 21324>>();

    check(DefaultFactorySourceAccess::count(factory) == 70);
    for (int type : expectedTypes) {
      auto *item = factory.createType(type);
      check(item && item->getData().type == unsigned(type));
      delete item;
    }
  }
  // Warm provider state isolates real per-instance allocation exceptions; every
  // successful allocation before each injected C++ bad_alloc is actually freed.
  for (unsigned failure = 1; failure <= nativeAllocations; ++failure) {
    alignas(EventFactory) unsigned char storage[sizeof(EventFactory)]{};
    auto *factory = reinterpret_cast<EventFactory *>(storage);
    resetAllocations(failure);
    bool caught = false;
    try {
      originalC1(factory);
    } catch (const std::bad_alloc &) {
      caught = true;
    }
    check(caught);
    assertFreed();
  }
  std::cout << "actual Factory35 production-object bootstrap PASS: mapcount35, "
               "lifecycle="
            << lifecycleCases
            << ", duplicate mapcount70, real warm allocation failures="
            << nativeAllocations << '\n';
}
