#include "presonus/uc/midi_connection.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>

using Presonus::UC::IMidiEventHandler;
using Presonus::UC::MidiConnection;
using Presonus::UC::MidiEvent;

namespace {
void *armed = nullptr;
unsigned sizedDeletes = 0;
unsigned unsizedDeletes = 0;
std::size_t observedSize = 0;

struct Recorder : IMidiEventHandler {
  const MidiEvent *seen = nullptr;
  unsigned calls = 0;
  void handleMidiEvent(const MidiEvent &value) override {
    seen = &value;
    ++calls;
  }
};

using AbiFunction = void (*)(MidiConnection *);
extern "C" void
originalC1(MidiConnection *) asm("_ZN8Presonus2UC14MidiConnectionC1Ev");
extern "C" void
originalC2(MidiConnection *) asm("_ZN8Presonus2UC14MidiConnectionC2Ev");
extern "C" void
originalD1(MidiConnection *) asm("_ZN8Presonus2UC14MidiConnectionD1Ev");
extern "C" void
originalD0(MidiConnection *) asm("_ZN8Presonus2UC14MidiConnectionD0Ev");
extern "C" bool originalDeliver(MidiConnection *, const MidiEvent &) asm(
    "_ZN8Presonus2UC14MidiConnection7deliverERKNS0_9MidiEventE");

void checkLiveVtable(MidiConnection *connection) {
  const unsigned char *slots = nullptr;
  std::memcpy(&slots, connection, sizeof(slots));
  const std::array<std::uintptr_t, 3> expected{
      reinterpret_cast<std::uintptr_t>(&originalD1),
      reinterpret_cast<std::uintptr_t>(&originalD0),
      reinterpret_cast<std::uintptr_t>(&originalDeliver)};
  for (std::size_t index = 0; index < expected.size(); ++index) {
    std::uintptr_t value = 0;
    std::memcpy(&value, slots + index * sizeof(value), sizeof(value));
    assert(value == expected[index]);
  }
}
} // namespace

extern "C" void __real__ZdlPv(void *pointer);
extern "C" void __real__ZdlPvm(void *pointer, std::size_t size);

extern "C" void __wrap__ZdlPv(void *pointer) {
  if (pointer == armed && armed) {
    ++unsizedDeletes;
    armed = nullptr;
  }
  __real__ZdlPv(pointer);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  if (pointer == armed && armed) {
    ++sizedDeletes;
    observedSize = size;
    armed = nullptr;
  }
  __real__ZdlPvm(pointer, size);
}

int main() {
  Recorder first, second;
  std::array<unsigned char, 8> sysex{0xf0, 1, 2, 3, 4, 5, 6, 0xf7};
  unsigned constructors = 0, deliveries = 0, callbacks = 0, destructors = 0;
  const std::array<AbiFunction, 2> constructorsBySymbol{originalC1, originalC2};
  for (auto construct : constructorsBySymbol) {
    for (unsigned char fill : {0, 0x5a, 0xff}) {
      for (IMidiEventHandler *handler :
           {static_cast<IMidiEventHandler *>(nullptr),
            static_cast<IMidiEventHandler *>(&first),
            static_cast<IMidiEventHandler *>(&second)}) {
        alignas(MidiConnection)
            std::array<unsigned char, sizeof(MidiConnection) + 64>
                bytes;
        bytes.fill(fill);
        auto *connection =
            reinterpret_cast<MidiConnection *>(bytes.data() + 32);
        construct(connection);
        checkLiveVtable(connection);
        ++constructors;
        assert(connection->portableHandler() == nullptr);
        connection->setPortableHandler(handler);
        for (unsigned mode = 0; mode < 3; ++mode) {
          MidiEvent event;
          std::fill_n(reinterpret_cast<unsigned char *>(&event), sizeof(event),
                      fill);
          event.portableSizeWord = 20;
          event.messageWord = mode == 0   ? 0x007f4090
                              : mode == 1 ? 0
                                          : 0xffffffffu;
          event.sysexData = mode == 0 ? nullptr : sysex.data();
          event.sysexLength = mode == 0 ? 0 : mode == 1 ? 3 : 8;
          event.trailingWord = 0;
          std::array<unsigned char, sizeof(MidiEvent)> eventBefore;
          std::memcpy(eventBefore.data(), &event, sizeof(event));
          const unsigned previous = first.calls + second.calls;
          assert(connection->deliver(event) == (handler != nullptr));
          assert(first.calls + second.calls ==
                 previous + unsigned(handler != nullptr));
          if (handler)
            assert(static_cast<Recorder *>(handler)->seen == &event);
          assert(connection->portableHandler() == handler);
          assert(std::memcmp(eventBefore.data(), &event, sizeof(event)) == 0);
          ++deliveries;
          callbacks += handler != nullptr;
        }
        const unsigned previous = first.calls + second.calls;
        originalD1(connection);
        ++destructors;
        assert(first.calls + second.calls == previous);
        for (std::size_t index = 0; index < 32; ++index) {
          assert(bytes[index] == fill);
          assert(bytes[32 + sizeof(MidiConnection) + index] == fill);
        }
      }
    }
  }
  // Actual base-sized allocations avoid mismatched base-D0/derived-allocation
  // probes. The native imported delete really frees each armed allocation.
  for (unsigned mode = 0; mode < 3; ++mode) {
    MidiConnection *connection = new MidiConnection;
    checkLiveVtable(connection);
    ++constructors;
    connection->setPortableHandler(mode == 0   ? nullptr
                                   : mode == 1 ? &first
                                               : &second);
    armed = connection;
    const unsigned previous = sizedDeletes + unsizedDeletes;
    if (mode == 0)
      originalD0(connection);
    else
      delete connection;
    ++destructors;
    assert(armed == nullptr && sizedDeletes + unsizedDeletes == previous + 1);
  }
  assert(sizedDeletes == 3 && unsizedDeletes == 0);
  assert(observedSize == sizeof(MidiConnection));
  assert(constructors == 21 && deliveries == 54 && callbacks == 36 &&
         destructors == 21);
  std::cout << "{\"passed\":true,\"constructors\":" << constructors
            << ",\"constructor_entry_probes\":18"
            << ",\"live_vtable_checks\":21"
            << ",\"deliveries\":" << deliveries
            << ",\"callbacks\":" << callbacks
            << ",\"destructors\":" << destructors
            << ",\"actual_sized_deletes\":" << sizedDeletes
            << ",\"native_object_size\":" << sizeof(MidiConnection) << "}\n";
}
