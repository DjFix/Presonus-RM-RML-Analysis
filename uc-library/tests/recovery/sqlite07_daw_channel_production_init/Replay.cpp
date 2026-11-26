#include "presonus/DAWChannel.hpp"
#include "presonus/DAWDeviceFolder.hpp"
#include "presonus/DAWDeviceSlot.hpp"
#include "presonus/mixer_dsp/Formatters.hpp"

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include <string_view>
#include <vector>

namespace {

using namespace Core::Portable;

void require(bool valid) {
  if (!valid)
    std::abort();
}

// Compare the primary vtable address point of live GNU/Linux host objects.
std::uintptr_t formatterVtable(const Core::Formatter &formatter) {
  std::uintptr_t addressPoint;
  std::memcpy(&addressPoint, &formatter, sizeof(addressPoint));
  return addressPoint;
}

struct InspectParameter : NumericParam {
  static const ParamInfo &descriptor(const Parameter &parameter) {
    return *(parameter.*&InspectParameter::info);
  }

  static bool feedback(const Parameter &parameter) {
    return (parameter.*&InspectParameter::flags & kFeedback) != 0;
  }
};

struct Channel : Presonus::DAWChannel {
  void add(Parameter *parameter) { paramList.add(parameter); }

  void prefill(Parameter *parameter) {
    for (auto &cache : cachedParameters_)
      cache = parameter;
  }

  std::array<Parameter *, 3> caches() const {
    return {cachedParameters_[selectedCache],
            cachedParameters_[channelStateCache], cachedParameters_[idCache]};
  }

  Parameter *lookup(int tag) const { return getParameterByTag(tag); }
};

struct RemovedObserver : ParamObserverBase {
  explicit RemovedObserver(const Channel &channel) : channel(channel) {}
  const Channel &channel;
  std::vector<int> tags;
  std::vector<std::array<float, 2>> rangeStates;

  void paramChanged(Parameter *parameter, int event) override {
    if (event == Parameter::kDestroyed) {
      const int tag = parameter->getTag();
      require(channel.lookup(tag) == nullptr);
      tags.push_back(tag);
      parameter->removeObserver(this);
    } else if (event == Parameter::kChanged && parameter->getTag() == 21) {
      rangeStates.push_back({parameter->getMin(), parameter->getMax()});
    }
  }
};

struct Folder : Presonus::DAWDeviceFolder {
  Folder(std::vector<int> &trace, int number) : trace(trace), number(number) {}
  std::vector<int> &trace;
  int number;

  void *castTo(int id) override {
    if (id == kTypeID)
      trace.push_back(number);
    return DAWDeviceFolder::castTo(id);
  }
};

struct Slot : Presonus::DAWDeviceSlot {
  Slot(std::vector<int> &trace, int number) : trace(trace), number(number) {}
  std::vector<int> &trace;
  int number;

  void *castTo(int id) override {
    if (id == kTypeID)
      trace.push_back(number);
    return DAWDeviceSlot::castTo(id);
  }
};

struct Foreign : Component {
  explicit Foreign(std::vector<int> &trace) : trace(trace) {}
  std::vector<int> &trace;

  void *castTo(int id) override {
    if (id == Presonus::DAWDeviceFolder::kTypeID)
      trace.push_back(0);
    return Component::castTo(id);
  }
};

ParamInfo info(int tag, const char *name, float value,
               int type = ParamInfo::kFloat) {
  ParamInfo result{};
  result.tag = tag;
  result.type = type;
  std::strcpy(result.name, name);
  result.minValue = -2.f;
  result.maxValue = 3.f;
  result.defaultValue = value;
  return result;
}

void printTags(const char *prefix, const std::vector<int> &tags) {
  std::printf("%s", prefix);
  for (int tag : tags)
    std::printf(":%d", tag);
  std::putchar('\n');
}

void printExtension(const Parameter &parameter) {
  const auto &d = InspectParameter::descriptor(parameter);
  require(!d.unitName && !d.curveName && !d.stringList && !d.title &&
          !d.shortTitle);
  std::printf("extension:%d:%d:%s:%g:%g:%g:%g:%g:%d:%d\n", d.type, d.tag,
              d.name, d.minValue, d.maxValue, d.midValue, d.defaultValue,
              d.deltaValue, d.flags, parameter.isOwnInfo() ? 1 : 0);
}

void replay(std::string_view profile, bool removeControls) {
  const bool full = profile == "full";
  const bool partial = profile == "partial";
  require(full || partial || profile == "empty");
  const std::vector<int> tags =
      full      ? std::vector<int>{0, 5, 6, 8, 9, 18, 21, 22, 23, 91}
      : partial ? std::vector<int>{5, 6, 21, 23, 91}
                : std::vector<int>{};
  const auto staleInfo = info(-1, "stale", 0.f);
  NumericParam stale(staleInfo);
  std::vector<int> folderCalls;
  Channel channel;
  RemovedObserver removed(channel);
  channel.prefill(&stale);
  NumericParam *range = nullptr;
  for (int tag : tags) {
    char name[32];
    std::snprintf(name, sizeof(name), "tag-%d", tag);
    if (tag == 22) {
      auto *parameter =
          new StringParam(info(tag, name, 0.f, ParamInfo::kString), true);
      parameter->fromString("fixture-channel-id", false);
      channel.add(parameter);
    } else if (partial && tag == 21) {
      static Core::CStringPtr labels[] = {"zero", "one", "two", "three"};
      auto listInfo = info(tag, name, 2.f, ParamInfo::kList);
      listInfo.minValue = 0.f;
      listInfo.stringList = labels;
      range = new ListParam(listInfo, true);
      channel.add(range);
    } else {
      auto *parameter = new NumericParam(info(tag, name, .5f), true);
      channel.add(parameter);
      if (tag == 21)
        range = parameter;
    }
    channel.lookup(tag)->addObserver(&removed);
  }

  std::vector<std::array<Parameter *, 2>> folderParameters;
  auto addFolder = [&](int number) {
    auto *folder = new Folder(folderCalls, number);
    auto *slot = new Slot(folderCalls, -number);
    const auto countInfo = info(0, "count", 1.f);
    const auto editInfo = info(7, "edit", 0.f);
    folder->addParameters(&countInfo, 1, true);
    slot->addParameters(&editInfo, 1, true);
    folder->addChild(slot);
    channel.addChild(folder);
    folderParameters.push_back(
        {folder->getParameterByTag(0), slot->getParameterByTag(7)});
  };
  Parameter *foreignParameter = nullptr;
  if (full || partial) {
    addFolder(1);
    auto *foreign = new Foreign(folderCalls);
    const auto foreignInfo = info(0, "foreign", 0.f);
    foreign->addParameters(&foreignInfo, 1, true);
    foreignParameter = foreign->getParameterByTag(0);
    channel.addChild(foreign);
  }
  if (full)
    addFolder(2);

  channel.init(removeControls);
  require(folderCalls == (full      ? std::vector<int>{1, -1, 0, 2, -2}
                          : partial ? std::vector<int>{1, -1, 0}
                                    : std::vector<int>{}));
  require(!foreignParameter || !InspectParameter::feedback(*foreignParameter));
  printTags("removed", removed.tags);
  std::vector<int> present;
  std::vector<int> feedback;
  for (int tag : tags) {
    if (auto *parameter = channel.lookup(tag)) {
      present.push_back(tag);
      if (InspectParameter::feedback(*parameter))
        feedback.push_back(tag);
      parameter->removeObserver(&removed);
    }
  }
  printTags("present", present);
  std::printf("caches");
  const auto caches = channel.caches();
  constexpr int cacheTags[] = {6, 0, 22};
  for (size_t index = 0; index < caches.size(); ++index) {
    const auto *parameter = caches[index];
    require(parameter == channel.lookup(cacheTags[index]));
    if (parameter)
      std::printf(":%d", parameter->getTag());
    else
      std::printf(":null");
  }
  std::putchar('\n');
  require(channel.isSelected() == (channel.lookup(6) != nullptr));
  const auto *id = channel.getID();
  require(channel.lookup(22)
              ? (id && std::strcmp(id, "fixture-channel-id") == 0)
              : id == nullptr);
  printTags("feedback", feedback);
  if (const auto *gain = channel.lookup(8)) {
    const auto *formatter = gain->getFormatter();
    const Presonus::Dsp::GainDBFormatter expected(true);
    require(formatter &&
            formatterVtable(*formatter) == formatterVtable(expected));
    char output[32];
    gain->toString(output, sizeof(output));
    require(std::strcmp(output, "-6.0 dB") == 0);

    Channel second;
    constexpr ParamInfo secondGain{
        ParamInfo::kFloat, 8,       "gain",  0,       1,      0, .5f, 0, 0,
        nullptr,           nullptr, nullptr, nullptr, nullptr};
    second.addParameters(&secondGain, 1, false);
    second.init(false);
    require(second.lookup(8)->getFormatter() == formatter);
    std::printf("gain:%s\n", formatter->getName());
  } else {
    std::puts("gain:null");
  }
  if (channel.lookup(21)) {
    require(range == channel.lookup(21));
    const auto expectedRangeStates =
        partial ? std::vector<std::array<float, 2>>{{0.f, 1.f}}
                : std::vector<std::array<float, 2>>{{0.f, 3.f}, {0.f, 1.f}};
    require(removed.rangeStates == expectedRangeStates);
    std::printf("range:%g:%g:%g\n", range->getMin(), range->getMax(),
                range->getValue());
  } else {
    std::puts("range:null");
  }
  require(channel.countParameters() == static_cast<int>(present.size()) + 3);
  for (int index = channel.countParameters() - 3;
       index < channel.countParameters(); ++index)
    printExtension(*channel.getParameterAt(index));
  for (const auto &pair : folderParameters)
    std::printf("folder:%d:%d\n", InspectParameter::feedback(*pair[0]),
                InspectParameter::feedback(*pair[1]));
}

} // namespace

int main(int argc, char **argv) {
  require(argc == 3);
  const std::string_view mode = argv[2];
  require(mode == "0" || mode == "1");
  replay(argv[1], mode == "1");
}
