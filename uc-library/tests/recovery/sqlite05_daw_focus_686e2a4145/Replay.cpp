#include "presonus/uc/ClientComponent.hpp"
#ifndef DAW_FOCUS_PROVIDER_ONLY
#include "presonus/DAWFocusChannel.hpp"
#endif
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>

using namespace Core::Portable;
using Presonus::UC::ClientComponent;

namespace {
const void *receiver = nullptr;
int receiverReleases = 0;
int releasedAfterCleanup = 0;
int childDeaths = 0;
int parameterDeaths = 0;

class OwnedChild final : public Component {
public:
  OwnedChild() : Component("child") {}
  ~OwnedChild() override { ++childDeaths; }
};

class TestParameter final : public NumericParam {
public:
  explicit TestParameter(const ParamInfo &info) : NumericParam(info) {}
  ~TestParameter() override { ++parameterDeaths; }
  bool feedback() const { return (flags & kFeedback) != 0; }
};

class ComponentAccess : public ClientComponent {
public:
  static auto parameters() { return &ComponentAccess::paramList; }
};

#ifndef DAW_FOCUS_PROVIDER_ONLY
using Presonus::DAWFocusChannel;
class FocusAccess : public DAWFocusChannel {
public:
  static auto cache() { return &FocusAccess::focusParameter_; }
};
#endif

ParamInfo makeInfo(int tag, const char *name) {
  ParamInfo info{};
  info.tag = tag;
  info.type = ParamInfo::kFloat;
  std::strcpy(info.name, name);
  return info;
}

const ParamInfo zeroInfo = makeInfo(0, "focus");
const ParamInfo otherInfo = makeInfo(9, "other");

void populate(Component &obj, int children, int params) {
  Component *parent = &obj;
  for (int n = 0; n < children; ++n) {
    auto *child = new OwnedChild;
    parent->addChild(child);
    parent = child;
  }
  if (params >= 1)
    obj.addParameters(&zeroInfo, 1);
  if (params >= 2)
    parent->addParameters(&otherInfo, 1);
}

class DestructionObserver final : public IParamObserver {
public:
  void *castTo(TypeID) override { return nullptr; }
  void paramChanged(Parameter *, int message) override {
    if (message == Parameter::kDestroyed)
      ++parameterDeaths;
  }
};

void observeDestruction(Component &obj, DestructionObserver &observer) {
  for (int n = 0; n < obj.countParameters(); ++n)
    obj.getParameterAt(n)->addObserver(&observer);
  for (int n = 0; n < obj.countChildren(); ++n)
    observeDestruction(*obj.getChild(n), observer);
}

bool empty(const Component &object) {
  return std::strcmp(object.getName(), "") == 0 && !object.getParent() &&
         !object.countChildren() && !object.countParameters();
}

void report() {
  std::cout << childDeaths << ' ' << parameterDeaths << ' ' << receiverReleases
            << ' ' << releasedAfterCleanup << std::endl;
}

class InitState {
public:
  explicit InitState(Component &owner)
      : parameters(owner.*ComponentAccess::parameters()) {}
  ~InitState() { delete detached; }

  void configure(int tagZero, int other) {
    if (other && !alternate) {
      alternate = new TestParameter(otherInfo);
      parameters.add(alternate);
    }
    if (tagZero && !zero) {
      zero = new TestParameter(zeroInfo);
      parameters.add(zero);
    } else if (!tagZero && zero) {
      if (detached)
        std::abort();
      detached = zero;
      parameters.remove(zero);
      zero = nullptr;
    }
  }

  TestParameter *lookup(int tag) {
    return static_cast<TestParameter *>(parameters.byTag(tag));
  }

  bool zeroFeedback() const { return zero && zero->feedback(); }
  bool otherFeedback() const { return alternate && alternate->feedback(); }

private:
  ParamList &parameters;
  TestParameter *zero = nullptr;
  TestParameter *alternate = nullptr;
  TestParameter *detached = nullptr;
};

int provider(const std::string &mode) {
  if (mode == "provider-ctor") {
    ClientComponent object("");
    std::cout << empty(object) << std::endl;
    return 0;
  }
  if (mode == "provider-init") {
    ClientComponent object("");
    InitState state(object);
    TestParameter *found = nullptr;
    std::string command;
    int first, second;
    while (std::cin >> command) {
      if (command == "configure") {
        std::cin >> first >> second;
        state.configure(first, second);
        std::cout << 1 << std::endl;
      } else if (command == "lookup") {
        std::cin >> first;
        found = state.lookup(first);
        std::cout << (found != nullptr) << std::endl;
      } else if (command == "feedback") {
        std::cin >> first;
        if (!found)
          return 1;
        found->setFeedbackNeeded(first != 0);
        std::cout << 1 << std::endl;
      } else if (command == "report") {
        std::cout << state.zeroFeedback() << ' ' << state.otherFeedback()
                  << std::endl;
      } else {
        return 1;
      }
    }
    return 0;
  }
  if (mode != "provider-dtor")
    return 1;

  int children, params;
  std::cin >> children >> params;
  void *storage = ::operator new(sizeof(ClientComponent));
  auto *object = ::new (storage) ClientComponent("");
  DestructionObserver observer;
  populate(*object, children, params);
  observeDestruction(*object, observer);
  receiver = storage;
  bool active = true;
  bool allocated = true;
  std::string command;
  while (std::cin >> command) {
    if (command == "base" && active) {
      object->ClientComponent::~ClientComponent();
      active = false;
      std::cout << 1 << std::endl;
    } else if (command == "free" && !active && allocated) {
      ::operator delete(storage);
      allocated = false;
      std::cout << (receiverReleases == 1) << std::endl;
    } else if (command == "report" && !active) {
      report();
    } else {
      return 1;
    }
  }
  receiver = nullptr;
  if (active)
    return 1;
  if (allocated)
    ::operator delete(storage);
  return 0;
}

#ifndef DAW_FOCUS_PROVIDER_ONLY
extern "C" void
focusC1(DAWFocusChannel *) asm("_ZN8Presonus15DAWFocusChannelC1Ev");
extern "C" void
focusC2(DAWFocusChannel *) asm("_ZN8Presonus15DAWFocusChannelC2Ev");
extern "C" void
focusD1(DAWFocusChannel *) asm("_ZN8Presonus15DAWFocusChannelD1Ev");

[[gnu::noinline]] void deleteThroughBase(Component *object) { delete object; }
[[gnu::noinline]] bool focusDispatch(Component *object) {
  return object->castTo(0x44774643) == object &&
         static_cast<IParamObserver *>(object)->castTo(0x44774643) == object;
}

int product(const std::string &mode) {
  if (mode == "cast") {
    DAWFocusChannel object;
    int typeId;
    std::cin >> typeId;
    void *result = object.castTo(typeId);
    if (result && result != &object)
      return 1;
    std::cout << (result != nullptr) << std::endl;
  } else if (mode == "init") {
    DAWFocusChannel object;
    InitState state(object);
    if (object.*FocusAccess::cache())
      return 1;
    int tagZero, other;
    while (std::cin >> tagZero >> other) {
      state.configure(tagZero, other);
      object.init();
      auto *cached = object.*FocusAccess::cache();
      if (cached != object.getParameterByTag(0))
        return 1;
      std::cout << (cached != nullptr) << ' ' << state.zeroFeedback() << ' '
                << state.otherFeedback() << std::endl;
    }
  } else if (mode == "C1" || mode == "C2") {
    int prefill;
    std::cin >> prefill;
    alignas(DAWFocusChannel) unsigned char storage[sizeof(DAWFocusChannel)];
    std::memset(storage, prefill, sizeof(storage));
    auto *object = reinterpret_cast<DAWFocusChannel *>(storage);
    (mode == "C1" ? focusC1 : focusC2)(object);
    object = std::launder(object);
    std::cout << empty(*object) << ' ' << focusDispatch(object) << ' '
              << (object->*FocusAccess::cache() == nullptr) << std::endl;
    focusD1(object);
  } else if (mode == "D0" || mode == "D1") {
    int children, params;
    std::cin >> children >> params;
    void *storage = ::operator new(sizeof(DAWFocusChannel));
    auto *object = ::new (storage) DAWFocusChannel;
    DestructionObserver observer;
    populate(*object, children, params);
    observeDestruction(*object, observer);
    receiver = storage;
    if (mode == "D0")
      deleteThroughBase(object);
    else
      focusD1(object);
    report();
    receiver = nullptr;
    if (mode == "D1")
      ::operator delete(storage);
  } else {
    return 1;
  }
  return 0;
}
#endif
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *memory) {
  if (memory == receiver) {
    ++receiverReleases;
    releasedAfterCleanup = 1 + childDeaths + parameterDeaths;
  }
  __real__ZdlPv(memory);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  const std::string mode(argv[1]);
#ifdef DAW_FOCUS_PROVIDER_ONLY
  return provider(mode);
#else
  return mode.starts_with("provider-") ? provider(mode) : product(mode);
#endif
}
