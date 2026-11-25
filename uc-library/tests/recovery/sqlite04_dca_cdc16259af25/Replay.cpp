#include "presonus/mixer/DCALevelHandler.hpp"
#include "presonus/mixer/FilterGroupComponent.hpp"

#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <string>
#include <vector>

using namespace Core::Portable;
using Presonus::Mixer::DCALevelHandler;
using Presonus::Mixer::FilterGroupComponent;

namespace {
class Watcher final : public ParamObserverBase {
public:
  explicit Watcher(const char *label) : label_(label) {}
  void paramChanged(Parameter *, int message) override {
    std::cout << label_ << ' ' << message << '\n';
  }

private:
  const char *label_;
};

class OwnedChild final : public Component {
public:
  ~OwnedChild() override { std::cout << "owned-child-destroyed\n"; }
};

template <typename Member, class Tag, Member member> struct ObserveMember {
  friend Member memberPointer(Tag) { return member; }
};
struct TagField {
  friend int DCALevelHandler::*memberPointer(TagField);
};
struct BusyField {
  friend bool DCALevelHandler::*memberPointer(BusyField);
};
struct VectorField {
  friend Core::Vector<Parameter *> DCALevelHandler::*memberPointer(VectorField);
};
template struct ObserveMember<int DCALevelHandler::*, TagField,
                              &DCALevelHandler::tag_>;
template struct ObserveMember<bool DCALevelHandler::*, BusyField,
                              &DCALevelHandler::busy_>;
template struct ObserveMember<Core::Vector<Parameter *> DCALevelHandler::*,
                              VectorField, &DCALevelHandler::masters_>;

DCALevelHandler *receiverUnderTest = nullptr;
} // namespace

extern "C" void __real__ZdlPv(void *pointer);
extern "C" void __wrap__ZdlPv(void *pointer) {
  if (receiverUnderTest && pointer == receiverUnderTest) {
    std::cout << "receiver-freed\n";
    receiverUnderTest = nullptr;
  }
  __real__ZdlPv(pointer);
}

extern void constructBase(DCALevelHandler *, Parameter *, Parameter *, int) asm(
    "_ZN8Presonus5Mixer15DCALevelHandlerC2EPN4Core8Portable9ParameterES5_i");
extern void destroyComplete(DCALevelHandler *) asm(
    "_ZN8Presonus5Mixer15DCALevelHandlerD1Ev");
extern void
destroyBase(DCALevelHandler *) asm("_ZN8Presonus5Mixer15DCALevelHandlerD2Ev");

int main(int argc, char **argv) {
  if (argc != 6)
    return EXIT_FAILURE;
  const std::string mode(argv[1]);
  const int tag = std::stoi(argv[2]);
  const int count = std::stoi(argv[3]);
  const int gain = std::stoi(argv[4]);
  const bool alias = std::stoi(argv[5]) != 0;
  const ParamInfo levelInfo{ParamInfo::kFloat, 0, "level", -10000.f, 10000.f};
  const ParamInfo trimInfo{ParamInfo::kFloat, 0, "trim", -10000.f, 10000.f};
  const ParamInfo masterInfo{ParamInfo::kFloat, tag, "master", -10000.f,
                             10000.f,           0.f, 1.f};
  NumericParam level(levelInfo);
  NumericParam trim(trimInfo);
  auto *trimParam = alias ? &level : &trim;
  level.setValueFast(static_cast<float>(gain));
  Watcher first("level-first");
  Watcher second("level-second");
  Watcher trimObserver("trim");
  Watcher ownerParam("owned-param");
  if (mode == "ctor" || mode == "ctor-base" || mode == "provider") {
    level.addObserver(&first);
    level.addObserver(&second);
    trim.addObserver(&trimObserver);
    if (mode != "provider") {
      alignas(DCALevelHandler) unsigned char buffer[sizeof(DCALevelHandler)];
      DCALevelHandler *handler;
      if (mode == "ctor-base") {
        handler = reinterpret_cast<DCALevelHandler *>(buffer);
        constructBase(handler, &level, trimParam, tag);
        handler = std::launder(handler);
      } else {
        handler = ::new (static_cast<void *>(buffer))
            DCALevelHandler(&level, trimParam, tag);
      }
      const auto &masters = handler->*memberPointer(VectorField{});
      std::cout << "state " << (handler->*memberPointer(TagField{})) << ' '
                << (handler->*memberPointer(BusyField{})) << ' '
                << masters.count() << ' ' << masters.getCapacity() << ' '
                << (handler->getName()[0] == '\0') << '\n';
      destroyComplete(handler);
    } else {
      level.changed();
      trimParam->setValue(level.getValue(), false);
    }
    std::cout << "trim-value " << trimParam->getValue() << '\n';
    level.removeObserver(&first);
    level.removeObserver(&second);
    trim.removeObserver(&trimObserver);
    return EXIT_SUCCESS;
  }

  if (mode == "provider-destroy") {
    auto component = std::make_unique<Component>();
    component->addChild(new OwnedChild);
    component->addParameters(&masterInfo, 1);
    component->getParameterByTag(tag)->addObserver(&ownerParam);
    std::vector<std::unique_ptr<NumericParam>> borrowed;
    {
      Core::Vector<Parameter *> masters(0, 5);
      for (int i = 0; i < count; ++i) {
        auto param = std::make_unique<NumericParam>(masterInfo);
        masters.add(param.get());
        borrowed.push_back(std::move(param));
      }
    }
    component.reset();
    std::cout << "trim-after-detach " << gain << '\n';
    std::cout << "borrowed-still-live";
    for (const auto &param : borrowed)
      std::cout << ' ' << param->getValue();
    std::cout << '\n';
    return EXIT_SUCCESS;
  }

  std::vector<std::unique_ptr<FilterGroupComponent>> groups;
  auto *handler = new DCALevelHandler(&level, trimParam, tag);
  handler->addChild(new OwnedChild);
  handler->addParameters(&masterInfo, 1);
  handler->getParameterByTag(tag)->addObserver(&ownerParam);
  for (int i = 0; i < count; ++i) {
    auto group = std::make_unique<FilterGroupComponent>(
        FilterGroupComponent::SourcePortConstruction{});
    group->addParameters(&masterInfo, 1);
    handler->addDCAMaster(group.get());
    groups.push_back(std::move(group));
  }

  trim.addObserver(&trimObserver);
  receiverUnderTest = handler;
  if (mode == "d0")
    delete static_cast<Component *>(handler);
  else if (mode == "d1")
    destroyComplete(handler);
  else if (mode == "d2")
    destroyBase(handler);
  else
    return EXIT_FAILURE;

  level.setValueFast(static_cast<float>(gain + 1));
  std::cout << "trim-after-detach " << trim.getValue() << '\n';
  std::cout << "borrowed-still-live";
  for (const auto &group : groups)
    std::cout << ' ' << group->getParameterByTag(tag)->getValue();
  std::cout << '\n';
  trim.removeObserver(&trimObserver);
  if (receiverUnderTest) {
    receiverUnderTest = nullptr;
    ::operator delete(handler);
  }
}
