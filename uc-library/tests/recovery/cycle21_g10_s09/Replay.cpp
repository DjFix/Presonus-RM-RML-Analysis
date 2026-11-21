#include "presonus/dsp/Controller.hpp"
#include "presonus/mixer/EQComponent.hpp"

#include <array>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string_view>

namespace {
using namespace Presonus;
using Core::Portable::Component;
using Mixer::EQComponent;

struct Allocation {
  void *pointer = nullptr;
  const char *event = nullptr;
};
std::array<Allocation, 3> observed{};

void require(bool condition) {
  if (!condition)
    std::abort();
}

void observe(void *pointer, const char *event) {
  for (auto &allocation : observed)
    if (!allocation.pointer) {
      allocation = {pointer, event};
      return;
    }
  std::abort();
}

class Controller final : public Dsp::Controller {
public:
  explicit Controller(bool property)
      : Dsp::Controller(presonus::dsp::ControllerSourceTag{}),
        property_(property) {}
  void processIdle() override {}
  void doUpdates() override {}
  float getValue(int) const override { std::abort(); }
  float setValue(int, float) override { std::abort(); }

  void setTarget(Core::IPropertyHandler *target) override {
    require(!property_ && target == expected);
    require(sourceState().word04 == 0);
    Dsp::Controller::setTarget(target);
  }

  void release() override {
    std::cout << (property_ ? "property_release\n" : "controller_release\n");
    Dsp::Controller::release();
  }

  Core::IPropertyHandler *expected = nullptr;

private:
  bool property_;
};

template <class Base> [[gnu::noinline]] void deleteThroughBase(Base *receiver) {
  delete receiver;
}
} // namespace

void *operator new(std::size_t size) {
  if (auto *pointer = std::malloc(size == 0 ? 1 : size))
    return pointer;
  throw std::bad_alloc();
}

void operator delete(void *pointer) noexcept {
  const char *event = nullptr;
  for (auto &allocation : observed)
    if (pointer && allocation.pointer == pointer) {
      event = allocation.event;
      allocation = {};
      break;
    }
  std::free(pointer);
  if (event)
    std::cout << event << '\n';
}

void operator delete(void *pointer, std::size_t) noexcept {
  ::operator delete(pointer);
}

int main() {
  {
    EQComponent existing(EQComponent::SourcePortConstruction{}, "Existing");
    require(std::string_view(existing.getName()) == "Existing");
    require(Core::Portable::core_cast<EQComponent>(&existing) == &existing);
  }
  auto *controller = new Controller(false);
  auto *property = new Controller(true);
  controller->expected = property;
  observe(controller, "controller_delete");
  observe(property, "property_delete");
  alignas(EQComponent) std::byte receiverStorage[sizeof(EQComponent)];
  auto *receiver =
      new (receiverStorage) EQComponent(EQComponent::SourcePortAudioLifecycle{},
                                        "Scoped", controller, property, 0);
  receiver->EQComponent::~EQComponent();
  for (const auto &allocation : observed)
    require(!allocation.pointer);
}
