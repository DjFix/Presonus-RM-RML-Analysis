#include "presonus/dsp/SimpleController.hpp"
#include "presonus/dsp/ControllerProperties.hpp"

#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <new>

namespace Presonus::Dsp {
namespace {

constexpr Core::PropertyType targetProperty = 0x54617267;

struct UpdateRecord {
  int tag = 0;
  std::uint32_t value = 0;
};

struct IndividualUpdate : Core::Property {
  explicit IndividualUpdate(bool integer)
      : Property(integer ? 0x50617269 : 0x50617261, sizeof(IndividualUpdate)) {}
  int channel = 0;
  UpdateRecord record;
};

struct AggregateUpdate : Core::Property {
  explicit AggregateUpdate(bool integer)
      : Property(integer ? 0x6d70726f : 0x6d70726d, sizeof(AggregateUpdate)) {}
  int channel = 0;
  std::array<UpdateRecord, 60> records{};
  int count = 0;
};

static_assert(sizeof(IndividualUpdate) == 20);
static_assert(sizeof(AggregateUpdate) == 496);

const ParamDescriptor &
descriptorAt(const Core::ConstVector<ParamDescriptor *> &descriptors,
             int index) {
  auto *descriptor = descriptors.at(index);
  return descriptor ? *descriptor : *ParamDescriptorList::getError();
}

int integerValue(float value) {
  if (std::isnan(value))
    return 0;
  if (value >= 0x1p31f)
    return std::numeric_limits<int>::max();
  if (value <= -0x1p31f)
    return std::numeric_limits<int>::min();
  return static_cast<int>(value);
}

} // namespace

SimpleController::SimpleController(int id, const ParamDescriptorList *list)
    : Controller(id, list), values_(list ? list->sourceCount() : 0),
      pending_(list ? list->sourceCount() : 0) {
  if (!list)
    return;
  const auto &descriptors = list->sourceDescriptors();
  for (int index = 0; index < descriptors.count(); ++index) {
    const auto value = std::bit_cast<float>(
        descriptorAt(descriptors, index).sourceState().word14);
    if (!values_.add(value))
      throw std::bad_alloc{};
  }
}

SimpleController::~SimpleController() = default;

int SimpleController::findIndex(int tag) const {
  const auto &state = sourceState();
  if (!state.descriptors)
    return -1;
  const int count = state.descriptors->count();
  if (!state.lookupByTag)
    return tag >= 0 && tag < count ? tag : -1;
  for (int index = 0; index < count; ++index) {
    auto *descriptor = state.descriptors->at(index);
    if (descriptor && descriptor->sourceState().tag == tag)
      return index;
  }
  return -1;
}

float SimpleController::getValue(int tag) const {
  const int index = findIndex(tag);
  return index >= 0 && index < values_.count() ? values_.at(index) : 0.f;
}

float SimpleController::setValue(int tag, float value) {
  const int index = findIndex(tag);
  if (index < 0 || index >= values_.count())
    return 0.f;
  const auto *curve = descriptorAt(*sourceState().descriptors, index)
                          .sourceState()
                          .interpolator;
  const float minimum = curve ? curve->getMinRange() : 0.f;
  const float maximum = curve ? curve->getMaxRange() : 1.f;
  if (value < minimum)
    value = minimum;
  if (value > maximum)
    value = maximum;
  auto &stored = values_.at(index);
  if (value != stored) {
    stored = value;
    if (!pending_.contains(tag) && (pending_.count() < pending_.getCapacity() ||
                                    pending_.resize(pending_.count() + 1)))
      pending_.add(tag);
    sourceState().processDirty = 1;
  }
  return stored;
}

void SimpleController::setupProcess(const SetupProperty &property) {
  auto &state = sourceState();
  if (property.rate != std::bit_cast<float>(state.processRateBits)) {
    state.processRateBits = std::bit_cast<std::uint32_t>(property.rate);
    updateAll();
  }
}

void SimpleController::setProperty(const Core::Property &property) {
  Controller::setProperty(property);
  if (property.type == targetProperty)
    updateAll();
}

void SimpleController::updateAll() {
  pending_.removeAll();
  auto &state = sourceState();
  if (state.descriptors) {
    const auto &descriptors = *state.descriptors;
    for (int index = 0; index < descriptors.count(); ++index) {
      if (pending_.count() < pending_.getCapacity() ||
          pending_.resize(pending_.count() + 1))
        pending_.add(descriptorAt(descriptors, index).sourceState().tag);
    }
  }
  state.processDirty = 1;
}

bool SimpleController::isInternal(int) const { return false; }

void SimpleController::doUpdates() {
  const int count = pending_.count();
  if (!count || !sourceState().descriptors)
    return;
  const auto makeRecord = [&](int tag, int index, bool integer) {
    const float value = values_.at(index);
    return UpdateRecord{
        tag, integer ? std::bit_cast<std::uint32_t>(integerValue(value))
                     : std::bit_cast<std::uint32_t>(value)};
  };
  const auto send = [this](auto &property) {
    property.channel = std::bit_cast<int>(sourceState().word04);
    Controller::sendProperty(static_cast<Core::Property &>(property));
  };
  const auto validIndex = [&](int index) {
    return index >= 0 && index < values_.count();
  };
  const auto isInteger = [&](int index) {
    return descriptorAt(*sourceState().descriptors, index)
               .sourceState()
               .word10 != 0;
  };
  if (count == 1) {
    const int tag = pending_.at(0);
    if (isInternal(tag))
      return;
    const int index = findIndex(tag);
    if (validIndex(index)) {
      const bool integer = isInteger(index);
      IndividualUpdate property(integer);
      property.record = makeRecord(tag, index, integer);
      send(property);
    }
    pending_.removeAll();
    return;
  }
  AggregateUpdate floats(false);
  AggregateUpdate integers(true);
  for (int position = 0; position < count; ++position) {
    const int tag = pending_.at(position);
    if (isInternal(tag))
      continue;
    const int index = findIndex(tag);
    if (!validIndex(index))
      continue;
    const bool integer = isInteger(index);
    auto &property = integer ? integers : floats;
    if (property.count == static_cast<int>(property.records.size())) {
      send(property);
      property.count = 0;
    }
    property.records[property.count++] = makeRecord(tag, index, integer);
  }
  if (floats.count)
    send(floats);
  if (integers.count)
    send(integers);
  pending_.removeAll();
}

} // namespace Presonus::Dsp
