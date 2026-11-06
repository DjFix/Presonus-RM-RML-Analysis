#include "presonus/AltMemoryFilter.hpp"
#include "presonus/mixer/ChannelParamTagFilter.hpp"
#include "presonus/mixer/ChannelParameterController.hpp"
#include "presonus/mixer/FxPresetFilter.hpp"
#include "presonus/mixer/GEQPresetFilter.hpp"
#include "presonus/mixer/SmaartStoreFilter.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
using namespace Presonus::Mixer;
using namespace Core::Portable;
namespace {
struct Services : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const ChannelComponent &) const override { return false; }
  void removeLink(ChannelComponent &) override {}
  ChannelComponent *linkablePair(ChannelComponent &) override {
    return nullptr;
  }
  void faderLocateDirty(ChannelComponent &) override {}
  void coefficientsChanged(ChannelComponent &, bool) override {}
};
struct Observer : ParamObserverBase {
  int edits = 0, changes = 0;
  void paramChanged(Parameter *, int msg) override {
    edits += msg == Parameter::kEdit;
    changes += msg == Parameter::kChanged;
  }
};
template <class Filter> struct Override : Filter {
  using Filter::Filter;
  mutable int calls = 0;
  int expectedType = 0;
  const char *expectedName = nullptr;
  void *expectedObject = nullptr;
  bool result = false;
  bool shouldLoad(int t, const char *n, void *o) const override {
    assert(t == expectedType && n == expectedName && o == expectedObject);
    ++calls;
    return result;
  }
};
template <class T>
bool saveCheck(T &f, int t, const char *n, void *o, bool result) {
  f.expectedType = t;
  f.expectedName = n;
  f.expectedObject = o;
  f.result = result;
  bool value = f.shouldSave(t, n, o);
  assert(f.calls == 1);
  return value;
}
} // namespace
int main(int argc, char **argv) {
  assert(argc == 13);
  const char *kind = argv[1];
  bool save = std::atoi(argv[2]);
  int type = std::strtoul(argv[3], nullptr, 10);
  const char *name = std::strcmp(argv[4], "<null>") == 0 ? nullptr : argv[4];
  bool present = std::atoi(argv[5]);
  int tag = std::atoi(argv[6]);
  unsigned flags = std::strtoul(argv[7], nullptr, 10);
  int controller = std::atoi(argv[8]), index = std::atoi(argv[9]),
      filtertag = std::atoi(argv[10]), filterindex = std::atoi(argv[11]);
  ParamInfo info = {};
  std::strncpy(info.name, argv[12], ParamInfo::kMaxNameLength - 1);
  info.tag = tag;
  info.flags = flags;
  NumericParam parameter(info);
  Services services;
  presonus::mixer::ChannelState state;
  ChannelComponent channel(state, services);
  ChannelParameterController owner(channel, index);
  Component other;
  // Real provider parameter registration, controller assignment and ownership.
  owner.addParameters(&info, 1);
  Parameter *registered = owner.getParameterAt(0);
  assert(registered &&
         registered->getController() == static_cast<IParamObserver *>(&owner));
  assert(core_cast<ChannelParameterController>(registered->getController()) ==
         &owner);
  assert(&owner.channel() == &channel && owner.channelIndex() == index);
  parameter.setController(
      controller == 2   ? static_cast<IParamObserver *>(&owner)
      : controller == 1 ? static_cast<IParamObserver *>(&other)
                        : nullptr);
  auto *eq = new Component("eq");
  if (controller == 2)
    owner.addChild(eq);
  else if (controller == 1)
    other.addChild(eq);
  void *object =
      present ? (type == Component::kTypeID ? static_cast<void *>(eq)
                                            : static_cast<void *>(&parameter))
              : nullptr;
  bool value = false;
  if (save) {
    if (!std::strcmp(kind, "FxPresetFilter")) {
      Override<FxPresetFilter> f;
      value = saveCheck(f, type, name, object, tag & 1);
    } else if (!std::strcmp(kind, "GEQPresetFilter")) {
      Override<GEQPresetFilter> f;
      value = saveCheck(f, type, name, object, tag & 1);
    } else if (!std::strcmp(kind, "ChannelParamTagFilter")) {
      Override<ChannelParamTagFilter> f(filtertag, filterindex);
      value = saveCheck(f, type, name, object, tag & 1);
    } else if (!std::strcmp(kind, "AltMemoryFilter")) {
      Override<AltMemoryFilter> f;
      value = saveCheck(f, type, name, object, tag & 1);
    } else {
      Override<SmaartStoreFilter> f;
      value = saveCheck(f, type, name, object, tag & 1);
    }
  } else {
    FxPresetFilter fx;
    GEQPresetFilter geq;
    ChannelParamTagFilter tags(filtertag, filterindex);
    AltMemoryFilter alt;
    SmaartStoreFilter smaart;
    IStorageFilter *filter = !std::strcmp(kind, "FxPresetFilter")
                                 ? static_cast<IStorageFilter *>(&fx)
                             : !std::strcmp(kind, "GEQPresetFilter")
                                 ? static_cast<IStorageFilter *>(&geq)
                             : !std::strcmp(kind, "ChannelParamTagFilter")
                                 ? static_cast<IStorageFilter *>(&tags)
                             : !std::strcmp(kind, "AltMemoryFilter")
                                 ? static_cast<IStorageFilter *>(&alt)
                                 : static_cast<IStorageFilter *>(&smaart);
    assert(core_cast<IStorageFilter>(filter) == filter);
    value = filter->shouldLoad(type, name, object);
    assert(filter->shouldSave(type, name, object) == value);
  }
  // The real parameter notification contract, no fake provider implementation.
  Observer observer;
  parameter.setController(&observer);
  parameter.setFeedbackNeeded(true);
  parameter.performEdit();
  parameter.changed();
  assert(observer.edits == 1 && observer.changes == 1);
  parameter.setController(nullptr);
  if (!controller)
    delete eq;
  std::cout << value << '\n';
}
