#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/CompressorComponent.hpp"
#include "presonus/mixer/EQComponent.hpp"
#include "presonus/mixer/FXBusComponent.hpp"
#include "presonus/mixer/FXComponent.hpp"
#include "presonus/mixer/FilterGroupComponent.hpp"
#include "presonus/mixer/GEQComponent.hpp"
#include "presonus/mixer/GateComponent.hpp"
#include "presonus/mixer/HPFilterComponent.hpp"
#include "presonus/mixer/LPFilterComponent.hpp"
#include "presonus/mixer/LimiterComponent.hpp"
#include "presonus/mixer/MasterSectionComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/MonoBusComponent.hpp"
#include "presonus/mixer/NetworkSelectComponent.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/mixer/SceneFilter.hpp"
#include "presonus/mixer/StereoLineComponent.hpp"
#include "presonus/mixer/TalkbackInputComponent.hpp"
#include <cstring>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <vector>
using namespace Core::Portable;
using namespace Presonus::Mixer;
namespace {
void require(bool condition) {
  if (!condition)
    throw std::runtime_error("SceneFilter provider/lifecycle mismatch");
}
float fromBits(unsigned bits) {
  float f;
  std::memcpy(&f, &bits, 4);
  return f;
}
ParamInfo info(int tag, int type = ParamInfo::kFloat) {
  ParamInfo p{};
  p.type = type;
  p.tag = tag;
  p.minValue = -std::numeric_limits<float>::infinity();
  p.maxValue = std::numeric_limits<float>::infinity();
  return p;
}
struct Settings : Component {
  std::array<ParamInfo, 10> descriptors;
  Settings(int missing = -999) {
    for (int i = 0; i < 10; ++i) {
      descriptors[i] = info(7 + i);
      if (7 + i != missing)
        addParameters(&descriptors[i], 1);
    }
  }
  void mask(unsigned mask) {
    const unsigned bits[] = {6, 7, 2, 3, 0, 4, 1, 5, 8, 9};
    for (int i = 0; i < 10; ++i)
      getParameterByTag(7 + i)->setValue(float((mask >> bits[i]) & 1), false);
  }
};
struct NonComponentObserver : ParamObserverBase {
  void paramChanged(Parameter *, int) override {
    throw std::runtime_error("observer callback");
  }
};
struct FXBoundary : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override {
    throw std::runtime_error("unrelated FX call");
  }
  unsigned getTypeNumber() override {
    throw std::runtime_error("unrelated FX call");
  }
  void updateTypeName() override {
    throw std::runtime_error("unrelated FX call");
  }
  void handleTypeChange(bool) override {
    throw std::runtime_error("unrelated FX call");
  }
};
struct NetworkBoundary : presonus::network_select::NetworkServices {
  void serverNotify(const Presonus::UC::MessageAttributes &) override {
    throw std::runtime_error("network call");
  }
  void scan(bool) override { throw std::runtime_error("network call"); }
  void idle() override { throw std::runtime_error("network call"); }
  void join(const char *, const char *) override {
    throw std::runtime_error("network call");
  }
  void updateList(ListParam *, ListParam *, ListParam *, bool) override {
    throw std::runtime_error("network call");
  }
  void suspendAdaptors(bool) override {
    throw std::runtime_error("network call");
  }
  void configureInterface(const char *) override {
    throw std::runtime_error("network call");
  }
  const char *managerName(const Presonus::WIFIManager &) const override {
    throw std::runtime_error("network call");
  }
  const char *managerSSID(const Presonus::WIFIManager &) const override {
    throw std::runtime_error("network call");
  }
  const char *managerIP(const Presonus::WIFIManager &, int) override {
    throw std::runtime_error("network call");
  }
  const void *find(const char *) override {
    throw std::runtime_error("network call");
  }
  bool hasFlag(const void *, const char *) override {
    throw std::runtime_error("network call");
  }
  const char *signalText(const void *) const override {
    throw std::runtime_error("network call");
  }
};
struct Types {
  presonus::mixer::ChannelState channel;
  Component parameters;
  ParamInfo pinfo = info(0);
  NumericParam p{pinfo};
  FXBoundary fxBoundary;
  presonus::mixer_fx::State fxState{parameters, p, p, fxBoundary};
  PermissionsBindings permissionsBindings;
  NetworkBoundary network;
  Presonus::DelayTimer timer{1};
  presonus::mixer_port::MasterBindings master{parameters, {}, timer};
  presonus::output_port::Bindings outputBindings{channel};
  OutputComponent output{outputBindings};
  presonus::send_output_port::SendState send{outputBindings};
  std::vector<presonus::send_output_port::SendState *> children;
  std::unique_ptr<Component> object;
  explicit Types(int kind) {
    switch (kind) {
    case 0:
      object = std::make_unique<Component>();
      break;
    case 1:
      object = std::make_unique<ChannelComponent>(
          ChannelComponent::SourcePortConstruction{}, channel);
      break;
    case 2:
      object =
          std::make_unique<EQComponent>(EQComponent::SourcePortConstruction{});
      break;
    case 3:
      object = std::make_unique<CompressorComponent>(
          CompressorComponent::SourcePortConstruction{});
      break;
    case 4:
      object = std::make_unique<GateComponent>(
          GateComponent::SourcePortConstruction{});
      break;
    case 5:
      object = std::make_unique<LimiterComponent>(
          LimiterComponent::SourcePortConstruction{});
      break;
    case 6:
      object = std::make_unique<HPFilterComponent>(
          HPFilterComponent::SourcePortConstruction{});
      break;
    case 7:
      object = std::make_unique<LPFilterComponent>(
          LPFilterComponent::SourcePortConstruction{});
      break;
    case 8:
      object = std::make_unique<GEQComponent>(
          GEQComponent::SourcePortConstruction{});
      break;
    case 9:
      object = std::make_unique<FXComponent>(fxState);
      break;
    case 10:
      object = std::make_unique<FilterGroupComponent>(
          FilterGroupComponent::SourcePortConstruction{});
      break;
    case 11:
      object = std::make_unique<PermissionsComponent>(permissionsBindings);
      break;
    case 12:
      object = std::make_unique<NetworkSelectComponent>(network);
      break;
    case 13:
      object = std::make_unique<MasterSectionComponent>(master);
      break;
    case 14:
      object = std::make_unique<MonoBusComponent>(
          ChannelComponent::SourcePortConstruction{}, channel);
      break;
    case 15:
      object = std::make_unique<FXBusComponent>(output, send, children);
      break;
    case 16:
      object = std::make_unique<StereoLineComponent>(
          ChannelComponent::SourcePortConstruction{}, channel);
      break;
    case 17:
      object = std::make_unique<TalkbackInputComponent>(
          ChannelComponent::SourcePortConstruction{}, channel);
      break;
    default:
      throw std::runtime_error("bad fixture class");
    }
    if (auto *c = core_cast<ChannelComponent>(object.get()))
      c->bindSourcePortState(channel);
    require(core_cast<Component>(object.get()) == object.get());
    require((core_cast<ChannelComponent>(object.get()) != nullptr) ==
            (kind == 1 || kind >= 14));
    require(core_cast<Component>(static_cast<IParamObserver *>(object.get())) ==
            object.get());
  }
};
struct TrackedNumeric : NumericParam {
  std::vector<int> &reads;
  int &destroyed;
  TrackedNumeric(const ParamInfo &p, std::vector<int> &r, int &d)
      : NumericParam(p), reads(r), destroyed(d) {}
  float getValue() const override {
    reads.push_back(getTag());
    return NumericParam::getValue();
  }
  ~TrackedNumeric() { ++destroyed; }
};
struct OwnedSettings : Component {
  void adopt(Parameter *p) { paramList.add(p); }
};
void lifecycle() {
  std::array<ParamInfo, 10> descriptors;
  std::vector<int> reads;
  int destroyed = 0;
  {
    OwnedSettings tracked;
    for (int i = 0; i < 10; ++i) {
      descriptors[i] = info(7 + i);
      tracked.adopt(new TrackedNumeric(descriptors[i], reads, destroyed));
    }
    MixerComponentBase owner;
    owner.sceneSettings = &tracked;
    {
      SceneFilter filter(owner);
      require(reads == std::vector<int>({7, 8, 9, 10, 11, 12, 13, 14, 15, 16}));
      reads.clear();
      filter.refresh();
      require(reads == std::vector<int>({7, 8, 9, 10, 11, 12, 13, 14, 15, 16}));
      reads.clear();
      SceneFilter copy(filter);
      require(reads == std::vector<int>({7, 8, 9, 10, 11, 12, 13, 14, 15, 16}));
    }
    require(destroyed == 0);
  }
  require(destroyed == 10);

  Settings a, b;
  a.mask(1);
  b.mask(512);
  MixerComponentBase mixer;
  mixer.sceneSettings = &a;
  {
    SceneFilter original(mixer);
    require(original.mask() == 1);
    auto *cached = original.cachedParameter(0);
    mixer.sceneSettings = &b;
    original.refresh();
    require(original.mask() == 1 && original.cachedParameter(0) == cached);
    original.setSceneRecallEnabled(false);
    SceneFilter copy(original);
    require(copy.mask() == 512 && copy.sceneRecallEnabled());
    require(copy.cachedParameter(0) == b.getParameterByTag(7));
    require(copy.castTo(IStorageFilter::kTypeID) ==
            static_cast<IStorageFilter *>(&copy));
    mixer.sceneSettings = nullptr;
    original.refresh();
    require(original.mask() == 0 && original.cachedParameter(0) == cached);
  }
  ChannelComponent partial(ChannelComponent::SourcePortConstruction{});
  bool rejected = false;
  try {
    partial.postDoUpdates();
  } catch (const std::logic_error &) {
    rejected = true;
  }
  require(rejected);
  for (int missing = 7; missing <= 16; ++missing) {
    Settings incomplete(missing);
    MixerComponentBase owner;
    SceneFilter candidate(owner);
    owner.sceneSettings = &incomplete;
    bool failed = false;
    try {
      candidate.refresh();
    } catch (const std::logic_error &) {
      failed = true;
    }
    require(failed);
    incomplete.addParameters(&incomplete.descriptors[missing - 7], 1);
    failed = false;
    try {
      candidate.refresh();
    } catch (const std::logic_error &) {
      failed = true;
    }
    require(failed == (missing != 7));
  }
  std::cerr << "real CCL typed hierarchy, borrowed cache retention, fresh "
               "copy, explicit partial-state rejection\n";
}
} // namespace
int main() {
  lifecycle();
  std::string op;
  while (std::cin >> op) {
    if (op == "D") {
      std::string mode, name;
      int kind, tag, enabled, matched, blocked, controller, configured,
          vectorKind;
      unsigned mask;
      std::cin >> mode >> kind >> tag >> mask >> enabled >> matched >>
          blocked >> controller >> name >> configured >> vectorKind;
      Types types(kind);
      Types vectorTypes(vectorKind);
      Settings settings;
      settings.mask(mask);
      MixerComponentBase mixer;
      mixer.sceneSettings = &settings;
      mixer.sceneRecallBlocksTag14 = blocked;
      mixer.sceneChannels = &mixer.inputChannels;
      auto pi = info(tag);
      NumericParam parameter(pi);
      NonComponentObserver observer;
      parameter.setController(
          controller ? static_cast<IParamObserver *>(types.object.get())
                     : nullptr);
      if (controller == 2)
        parameter.setController(&observer);
      types.channel.level = &parameter;
      vectorTypes.channel.level = &parameter;
      presonus::mixer::ChannelState otherState;
      otherState.level = &types.p;
      ChannelComponent unmatched(ChannelComponent::SourcePortConstruction{},
                                 otherState);
      // Exact native collection and level-field projection is bound separately
      // in native store evidence; original ARM layout remains excluded.
      if (matched >= 2)
        mixer.inputChannels.add(&unmatched);
      if (matched == 1 || matched == 2)
        if (auto *channel =
                core_cast<ChannelComponent>(vectorTypes.object.get()))
          mixer.inputChannels.add(channel);
      types.object->setName(name.c_str());
      auto gi = info(600, ParamInfo::kString);
      if (auto *group = core_cast<FilterGroupComponent>(types.object.get())) {
        group->addParameters(&gi, 1);
        StringParam::cast(group->getParameterByTag(600))
            ->fromString(configured ? "configured" : "");
      }
      SceneFilter filter(mixer);
      filter.setSceneRecallEnabled(enabled);
      int type = mode == "lp" || mode == "sp" ? Parameter::kTypeID
                 : mode == "lc" || mode == "sc" || mode == "ls" || mode == "ss"
                     ? Component::kTypeID
                     : 42;
      void *object =
          mode == "lp" || mode == "sp"   ? static_cast<void *>(&parameter)
          : mode == "ls" || mode == "ss" ? static_cast<void *>(&settings)
                                         : types.object.get();
      if (mode == "ln" || mode == "sn") {
        object = nullptr;
        type = Component::kTypeID;
      }
      bool result = mode[0] == 'l' ? filter.shouldLoad(type, nullptr, object)
                                   : filter.shouldSave(type, nullptr, object);
      require(filter.mask() == mask);
      std::cout << int(result) << '\n';
    } else if (op == "R") {
      int variant, present, cache, missing;
      std::array<unsigned, 10> values;
      std::cin >> variant >> present >> cache >> missing;
      for (auto &v : values)
        std::cin >> v;
      Settings settings(missing);
      MixerComponentBase mixer;
      std::unique_ptr<SceneFilter> filter;
      bool fault = false;
      try {
        if (variant == 0) {
          filter = std::make_unique<SceneFilter>(mixer);
          mixer.sceneSettings = present ? &settings : nullptr;
        } else
          mixer.sceneSettings = present ? &settings : nullptr;
        for (int i = 0; i < 10; ++i)
          if (auto *p = settings.getParameterByTag(7 + i))
            p->setValue(fromBits(values[i]), false);
        if (variant == 0)
          filter->refresh();
        else if (variant == 1 || variant == 3) {
          SceneFilter original(mixer);
          original.setSceneRecallEnabled(false);
          filter = std::make_unique<SceneFilter>(original);
        } else
          filter = std::make_unique<SceneFilter>(mixer);
      } catch (const std::logic_error &) {
        fault = true;
      }
      // Native missing-pointer fault is explicitly rejected. Native cached
      // complete pointer fixtures ignore missing lookup slots by definition.
      std::cout << int(fault) << ' ' << (filter ? filter->mask() : 0) << '\n';
    } else
      throw std::runtime_error("bad replay mode");
  }
}
