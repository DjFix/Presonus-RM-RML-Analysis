#include "core/public/corebuffer.h"
#include "presonus/DspComponent.hpp"
#include "presonus/LinkableComponent.hpp"
#include "presonus/dsp/Controller.hpp"
#include "presonus/mixer/AudioComponent.hpp"

#include <cassert>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <string_view>

namespace {
using namespace Presonus;
using Core::Portable::Component;
using Mixer::AudioComponent;

struct Allocation {
  void *pointer;
  const char *label;
};
Allocation observed[4]{};

void observeDelete(void *pointer, const char *label) {
  for (auto &allocation : observed)
    if (!allocation.pointer) {
      allocation = {pointer, label};
      return;
    }
  std::abort();
}

void recordDelete(void *pointer) {
  for (auto &allocation : observed)
    if (pointer && allocation.pointer == pointer) {
      std::cout << allocation.label << '\n';
      allocation = {};
      return;
    }
}

class Child final : public Component {
public:
  Child() : Component("child") {}
  ~Child() override { std::cout << "component\n"; }
};

void observeProviders(Core::Portable::Attributes &attributes,
                      Core::Portable::Component &component) {
  using Core::IO::Buffer;
  auto *buffer = new Buffer;
  observeDelete(buffer, "attributes");
  attributes.setInplaceBuffer(buffer);
  attributes.set("key", 7);
  component.addChild(new Child);
}

class Boundary final : public linkable_port::Boundary {
public:
  LinkableComponent *query(LinkableComponent &, std::uint32_t) override {
    std::abort();
  }
  void remove(LinkableComponent &) override { std::abort(); }
  void set(LinkableComponent &, LinkableComponent &, bool) override {
    std::abort();
  }
  void master(LinkableComponent &, LinkableComponent &) override {
    std::abort();
  }
};

class Controller final : public Dsp::Controller {
public:
  explicit Controller(bool property = false)
      : Dsp::Controller(presonus::dsp::ControllerSourceTag{}),
        property_(property) {}
  void processIdle() override {}
  void doUpdates() override {}
  float getValue(int) const override { std::abort(); }
  float setValue(int, float) override { std::abort(); }
  void release() override {
    std::cout << (property_ ? "property_release\n" : "controller_release\n");
    Dsp::Controller::release();
  }
  void setTarget(Core::IPropertyHandler *target) override {
    std::cout << "set_target " << sourceState().word04 << ' '
              << (target == expected) << '\n';
    Dsp::Controller::setTarget(target);
  }
  Core::IPropertyHandler *expected = nullptr;

private:
  bool property_;
};

template <class Base> class Derived : public Base {
public:
  using Base::Base;
};

template <class T> [[gnu::noinline]] void deletingDestructor(T *value) {
  delete value;
}

void linkable(int slot) {
  Boundary boundary;
  auto state = std::make_unique<linkable_port::State>();
  observeProviders(state->alternate, state->component);
  {
    linkable_port::State borrowed;
    auto *part = new Core::IO::Buffer;
    borrowed.alternate.setInplaceBuffer(part);
    {
      LinkableComponent object(borrowed, boundary);
    }
    assert(borrowed.alternate.getInplaceBuffer() == part);
  }
  if (slot == 1) {
    LinkableComponent complete(std::move(state), boundary);
  } else if (slot == 2) {
    Derived<LinkableComponent> base(std::move(state), boundary);
  } else {
    auto *receiver = new LinkableComponent(std::move(state), boundary);
    observeDelete(receiver, "receiver_delete");
    deletingDestructor(receiver);
  }
}

void dsp(int slot, bool present) {
  using dspcomponent_port::AdoptController;
  Controller *controller = present ? new Controller : nullptr;
  if (controller)
    observeDelete(controller, "controller_delete");
  {
    Controller borrowed;
    {
      DspComponent object("Borrowed", &borrowed);
      assert(object.getController() == &borrowed);
    }
  }
  if (slot == 4) {
    DspComponent complete("NativeLifecycle", controller, AdoptController{});
    observeProviders(complete.linkAttributes(), complete.coreComponent());
  } else if (slot == 5) {
    Derived<DspComponent> base("NativeLifecycle", controller,
                               AdoptController{});
    observeProviders(base.linkAttributes(), base.coreComponent());
  } else {
    auto *receiver =
        new DspComponent("NativeLifecycle", controller, AdoptController{});
    observeProviders(receiver->linkAttributes(), receiver->coreComponent());
    observeDelete(receiver, "receiver_delete");
    deletingDestructor(receiver);
  }
}

template <class T> void audio(int slot, int id) {
  auto *controller = new Controller;
  auto *property = new Controller(true);
  controller->expected = property;
  observeDelete(controller, "controller_delete");
  observeDelete(property, "property_delete");
  T receiver("NativeLifecycle", controller, property, id);
  assert(receiver.getController() == controller);
  assert(std::string_view(receiver.coreComponent().getName()) ==
         "NativeLifecycle");
  assert(controller->sourceState().target == property);
  assert(controller->sourceState().word04 == static_cast<std::uint32_t>(id));
  if (slot >= 9) {
    std::cout << "begin_destructor\n";
    observeProviders(receiver.linkAttributes(), receiver.coreComponent());
  } else {
    std::cout << "constructed\n";
  }
}
} // namespace

void *operator new(std::size_t size) {
  if (void *pointer = std::malloc(size == 0 ? 1 : size))
    return pointer;
  throw std::bad_alloc();
}

void operator delete(void *pointer) noexcept {
  recordDelete(pointer);
  std::free(pointer);
}

void operator delete(void *pointer, std::size_t) noexcept {
  ::operator delete(pointer);
}

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int slot = std::atoi(argv[1]);
  const bool present = std::atoi(argv[2]) != 0;
  const int id = std::atoi(argv[3]);
  if (slot >= 1 && slot <= 3)
    linkable(slot);
  else if (slot >= 4 && slot <= 6)
    dsp(slot, present);
  else if (slot == 7 || slot == 9)
    audio<AudioComponent>(slot, id);
  else if (slot == 8 || slot == 10)
    audio<Derived<AudioComponent>>(slot, id);
  else
    return 2;
  for (const auto &allocation : observed)
    assert(!allocation.pointer);
}
