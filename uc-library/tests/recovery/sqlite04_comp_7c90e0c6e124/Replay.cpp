#ifdef COMP_VECTOR_BOUNDARY
#include "core/portable/coreparams.h"
#include "core/public/coreinterpolator.h"
#include "core/public/corevector.h"
#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include <bit>
#include <cstdint>
#include <memory>

#include <iostream>
#include <string>

namespace {
void printRange(const Core::Interpolator &object) {
  std::cout << std::bit_cast<std::uint32_t>(object.getMinRange()) << ' '
            << std::bit_cast<std::uint32_t>(object.getMaxRange()) << std::endl;
}
} // namespace

int main() {
  presonus::dsp::registerEqSourcePortProviders();
  presonus::dsp::registerCompressorSourcePortProviders();
  std::unique_ptr<Core::Interpolator> pending;
  for (std::string operation; std::cin >> operation;) {
    if (operation == "resize") {
      int requested, delta;
      std::cin >> requested >> delta;
      Core::Vector<std::uint32_t> storage(0, delta);
      std::cout << (storage.resize(requested) ? storage.getCapacity() : -1)
                << std::endl;
    } else if (operation == "formatter" || operation == "create") {
      std::string name;
      std::cin >> name;
      if (name == "-")
        name.clear();
      if (operation == "formatter") {
        std::cout << (Core::FormatterRegistry::find(name.c_str()) != nullptr)
                  << std::endl;
      } else {
        pending.reset(Core::InterpolatorFactory::create(name.c_str()));
        std::cout << static_cast<bool>(pending) << std::endl;
      }
    } else if (operation == "range" || operation == "linear") {
      std::uint32_t minimum, maximum;
      std::cin >> minimum >> maximum;
      if (operation == "linear") {
        pending = std::make_unique<Core::LinearInterpolator>(
            std::bit_cast<float>(minimum), std::bit_cast<float>(maximum));
        printRange(*pending);
      } else {
        std::uint32_t midpoint;
        std::cin >> midpoint;
        if (!pending)
          return 2;
        pending->setRange(std::bit_cast<float>(minimum),
                          std::bit_cast<float>(maximum),
                          std::bit_cast<float>(midpoint));
        printRange(*pending);
        pending.reset();
      }
    } else {
      return 2;
    }
  }
}
#else
#include "presonus/dsp/CompController.hpp"
#include "presonus/mixer_dsp/CompressorSourceProviders.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include <bit>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <new>
#include <string>

using Comp = Presonus::Dsp::CompController;

extern "C" void constructBase(Comp *,
                              int) asm("_ZN8Presonus3Dsp14CompControllerC2Ei");
extern "C" void
destroyComplete(Comp *) asm("_ZN8Presonus3Dsp14CompControllerD1Ev");
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;

namespace {
void *receiver = nullptr;
void *targetAllocation = nullptr;
unsigned released = 0;
unsigned receiverFreed = 0;

void markFree(void *p) {
  if (p == targetAllocation)
    ++released;
  if (p == receiver) {
    ++receiverFreed;
    std::cout << "delete\n";
  }
}

class Target : public Core::IPropertyHandler {
public:
  void setProperty(const Core::Property &p) override {
    if (p.size != 304)
      std::abort();
    auto bytes = reinterpret_cast<const unsigned char *>(&p);
    for (int i = 0; i < p.size; ++i)
      std::cout << std::setfill('0') << std::setw(2) << std::hex
                << static_cast<int>(bytes[i]);
    std::cout << std::dec << '\n';
  }
  void getProperty(Core::Property &) override { std::abort(); }
  void release() override {
    delete this;
    if (released != 1)
      std::abort();
    std::cout << "release\n";
  }
};

void appendValues(const Comp &controller) {
  for (int i = 0; i < 10; ++i)
    std::cout << ' ' << std::bit_cast<std::uint32_t>(controller.getValue(i));
  std::cout << '\n';
}
} // namespace

extern "C" void __wrap__ZdlPv(void *p) noexcept {
  __real__ZdlPv(p);
  markFree(p);
}

extern "C" void __wrap__ZdlPvm(void *p, std::size_t s) noexcept {
  __real__ZdlPvm(p, s);
  markFree(p);
}

int main() {
  presonus::dsp::registerEqSourcePortProviders();
  presonus::dsp::registerCompressorSourcePortProviders();

  for (std::string operation; std::cin >> operation;) {
    if (operation == "construct") {
      int id, variant;
      std::cin >> id >> variant;
      alignas(Comp) std::byte storage[sizeof(Comp)];
      auto *controller = reinterpret_cast<Comp *>(storage);
      if (variant == 2)
        constructBase(controller, id);
      else
        controller = new (storage) Comp(id);
      const auto &state = controller->sourceState();
      std::cout << state.word08 << ' '
                << std::bit_cast<std::uint32_t>(state.constructorId) << ' '
                << static_cast<unsigned>(state.processDirty) << ' '
                << state.word20;
      appendValues(*controller);
      destroyComplete(controller);
    } else if (operation == "destroy") {
      int owns, attached, deleting;
      std::cin >> owns >> attached >> deleting;
      auto *controller = new Comp(0);
      auto *target = attached ? new Target : nullptr;
      receiver = controller;
      targetAllocation = target;
      released = receiverFreed = 0;
      controller->setTarget(target);
      if (owns)
        controller->makeTargetOwner();
      if (deleting)
        controller->release();
      else
        destroyComplete(controller);
      if (receiverFreed != static_cast<unsigned>(deleting) ||
          released != static_cast<unsigned>(owns && attached))
        std::abort();
      receiver = targetAllocation = nullptr;
      if (!deleting)
        ::operator delete(controller);
      if (attached && !owns)
        delete target;
      std::cout << "end\n";
    } else if (operation == "set") {
      int tag;
      std::uint32_t word;
      unsigned enabled, dirty;
      std::cin >> tag >> word >> enabled >> dirty;
      Comp controller(0);
      controller.setValue(0, static_cast<float>(enabled));
      auto &state = controller.sourceState();
      state.processDirty = dirty;
      state.word20 = 0;
      controller.setValue(tag, std::bit_cast<float>(word));
      std::cout << static_cast<unsigned>(state.processDirty) << ' '
                << state.word20;
      appendValues(controller);
    } else if (operation == "get") {
      int tag, setTag;
      std::uint32_t word;
      std::cin >> tag >> setTag >> word;
      Comp controller(0);
      controller.setValue(setTag, std::bit_cast<float>(word));
      auto before = controller.sourceState();
      std::cout << std::bit_cast<std::uint32_t>(controller.getValue(tag))
                << '\n';
      auto after = controller.sourceState();
      if (before.processDirty != after.processDirty ||
          before.word20 != after.word20)
        std::abort();
    } else if (operation == "update") {
      float enabled, soft, automatic, threshold, ratio, rate;
      int attached;
      std::cin >> enabled >> soft >> automatic >> threshold >> ratio >> rate >>
          attached;
      Comp controller(0);
      const float values[] = {enabled, soft, automatic, threshold,
                              ratio,   .02f, .6f,       7.f};
      for (int tag = 0; tag < 8; ++tag)
        controller.setValue(tag, values[tag]);
      controller.sourceState().processRateBits =
          std::bit_cast<std::uint32_t>(rate);
      controller.sourceState().word04 = 0x89abcdef;
      Target target;
      if (attached)
        controller.setTarget(&target);
      controller.doUpdates();
      std::cout << "end\n";
    } else {
      return 2;
    }
  }
}
#endif
