#include "presonus/mixer_dsp/EQ5Controller.hpp"
#include "presonus/mixer_dsp/Eq8LimiterParameterLists.hpp"

#include <bit>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

using Presonus::Dsp::Controller;
using Presonus::Dsp::EQ5Controller;

namespace {
const void *receiver;
const void *bands;
unsigned bandFrees;
unsigned receiverFrees;
unsigned releases;
unsigned sequence;
unsigned releaseSequence;
unsigned deleteSequence;
bool measuring;

class Target final : public Core::IPropertyHandler {
public:
  void setProperty(const Core::Property &) override {}
  void getProperty(Core::Property &) override {}
  void release() override {
    ++releases;
    releaseSequence = ++sequence;
  }
};

class Derived : public EQ5Controller {
public:
  explicit Derived(int id) : EQ5Controller(id) {}
};

void printState(EQ5Controller &object) {
  using Presonus::Dsp::Eq8ParamList;
  const auto &source = object.sourceState();
  assert(source.descriptorList ==
         &presonus::dsp::sourceList(*Eq8ParamList::instance()));
  std::printf("%u %d %d %u %u", static_cast<unsigned>(source.constructorId),
              object.getNumBands(), object.getNumParameters(),
              static_cast<unsigned>(object.portableEnabled()),
              static_cast<unsigned>(source.processDirty));
  for (const auto &band : object.portableBands()) {
    std::printf(
        " %d %u %u %u %u %u %u %u", band.type,
        std::bit_cast<unsigned>(band.frequency),
        std::bit_cast<unsigned>(band.q), std::bit_cast<unsigned>(band.gain),
        static_cast<unsigned>(band.enabled), static_cast<unsigned>(band.dirty),
        static_cast<unsigned>(band.edgeSelectable),
        static_cast<unsigned>(band.calculator.portableState().byte48));
  }
  const auto &descriptors = source.descriptorList->sourceDescriptors();
  for (int i = 0; i < descriptors.count(); ++i) {
    const auto &descriptor = descriptors.at(i)->sourceState();
    std::printf(" %d %u", descriptor.tag, descriptor.word14);
  }
  std::putchar('\n');
}

void observeDelete(void *pointer) {
  if (!measuring)
    return;
  if (pointer == receiver) {
    ++receiverFrees;
    deleteSequence = ++sequence;
  }
  if (pointer == bands)
    ++bandFrees;
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *pointer) {
  observeDelete(pointer);
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  observeDelete(pointer);
  __real__ZdlPvm(pointer, size);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  unsigned identifier;
  while (std::scanf("%u", &identifier) == 1) {
    const int id = std::bit_cast<int>(identifier);
    if (std::strcmp(argv[1], "c1") == 0) {
      EQ5Controller object(id);
      printState(object);
      continue;
    }
    if (std::strcmp(argv[1], "c2") == 0) {
      Derived object(id);
      printState(object);
      continue;
    }
    alignas(EQ5Controller) std::byte storage[sizeof(EQ5Controller)];
    const bool deleting = std::strcmp(argv[1], "d0") == 0;
    auto *object =
        deleting ? new EQ5Controller(id) : new (storage) EQ5Controller(id);
    Target target;
    if (identifier)
      object->setTarget(&target);
    if (identifier == 0xffffffffu)
      object->makeTargetOwner();
    receiver = object;
    bands = object->portableBands().data();
    bandFrees = receiverFrees = releases = sequence = releaseSequence =
        deleteSequence = 0;
    measuring = true;
    if (deleting) {
      Controller *base = object;
      delete base;
    } else {
      object->~EQ5Controller();
    }
    measuring = false;
    std::printf("%u %u %u %u %u\n", releases, bandFrees, receiverFrees,
                releaseSequence, deleteSequence);
  }
}
