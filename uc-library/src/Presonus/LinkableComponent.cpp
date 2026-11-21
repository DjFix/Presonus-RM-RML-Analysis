#include "presonus/LinkableComponent.hpp"
#include "core/portable/corepersistence.h"
#include "presonus/AltMemoryFilter.hpp"
#include <cstring>
#include <stdexcept>
#include <utility>
namespace Presonus {
namespace {
linkable_port::State &requireState(linkable_port::State *state) {
  if (!state)
    throw std::invalid_argument(
        "LinkableComponent requires owned provider state");
  return *state;
}
} // namespace

LinkableComponent::LinkableComponent(
    std::unique_ptr<linkable_port::State> state,
    linkable_port::Boundary &boundary)
    : ownedState_(std::move(state)), state_(requireState(ownedState_.get())),
      boundary_(boundary) {}

LinkableComponent::~LinkableComponent() = default;

void LinkableComponent::toggleAltMemory() {
  Core::Threads::ScopedLock lock(&linkable_port::State::alternateLock);
  Core::Portable::Attributes previous(state_.alternate);
  state_.alternate.removeAll();
  AltMemoryFilter filter;
  {
    Core::Portable::AttributePoolSuspender suspend;
    Core::Portable::AttributesBuilder builder(state_.alternate);
    Core::Portable::OutputStorage storage(builder, &filter);
    state_.component.save(storage);
  }
  if (!previous.isEmpty() && (!state_.partner || !state_.slave)) {
    Core::Portable::InputStorage storage(previous, &filter);
    state_.component.load(storage);
  }
}

void LinkableComponent::copyToAltMemory(Core::Portable::Attributes &source) {
  Core::Threads::ScopedLock lock(&linkable_port::State::alternateLock);
  Core::Portable::AttributePoolSuspender suspend;
  state_.alternate.removeAll();
  state_.alternate.copyFrom(source);
}
void LinkableComponent::loadAltMemory(
    const Core::Portable::InputStorage &storage) {
  if (std::strcmp(storage.getMode(), "ignoreAltMemory") == 0)
    return;
  Core::Threads::ScopedLock lock(&linkable_port::State::alternateLock);
  Core::Portable::AttributePoolSuspender suspend;
  state_.alternate.removeAll();
  if (const auto *alternate = storage.getAttributes().getAttributes("altmem")) {
    state_.alternate.copyFrom(*alternate);
    state_.alternate.makeReal();
  }
}
bool LinkableComponent::load(const Core::Portable::InputStorage &storage) {
  const bool loaded = state_.component.load(storage);
  if (loaded)
    loadAltMemory(storage);
  return loaded;
}

void LinkableComponent::syncParams(Core::Portable::Parameter &source,
                                   Core::Portable::Parameter &destination,
                                   bool edit) {
  using namespace Core::Portable;
  switch (source.getType()) {
  case ParamInfo::kString: {
    char text[256];
    text[0] = '\0';
    source.toString(text, sizeof(text));
    destination.fromString(text, edit);
    break;
  }
  case ParamInfo::kColor: {
    auto *sourceColor = ColorParam::cast(&source);
    auto *destinationColor = ColorParam::cast(&destination);
    if (sourceColor && destinationColor)
      destinationColor->setColor(sourceColor->getColor(), edit);
    break;
  }
  default:
    destination.setValue(source.getValue(), edit);
    break;
  }
}

bool LinkableComponent::save(Core::Portable::OutputStorage &storage) const {
  bool saved = state_.component.save(storage);
  if (!saved || std::strcmp(storage.getMode(), "ignoreAltMemory") == 0)
    return saved;
  Core::Threads::ScopedLock lock(&linkable_port::State::alternateLock);
  if (!state_.alternate.isEmpty()) {
    Core::Portable::AttributesWriter writer(storage.getWriter());
    writer.writeObject("altmem", state_.alternate,
                       Core::Portable::Attribute::kShareID);
  }
  return saved;
}

void LinkableComponent::linkAsSlave(LinkableComponent &partner) {
  if (state_.partner != &partner) {
    state_.slave = 1;
    state_.partner = &partner;
  }
}
void LinkableComponent::linkAsMaster(LinkableComponent &partner) {
  if (state_.partner == &partner)
    return;
  state_.partner = &partner;
  state_.slave = 0;
  partner.linkAsSlave(*this);

  if (state_.enabled) {
    for (int i = 0; i < state_.component.countParameters(); ++i) {
      auto *source = state_.component.getParameterAt(i);
      if (source->isLinkable())
        if (auto *destination =
                state_.partner->state_.component.getParameterByTag(
                    source->getTag()))
          syncParams(*source, *destination, true);
    }
    Core::Threads::ScopedLock lock(&linkable_port::State::alternateLock);
    partner.copyToAltMemory(state_.alternate);
  }

  auto *children = state_.children;
  const auto count = state_.count;
  for (std::size_t i = 0; i < count; ++i) {
    if (!children[i])
      continue;
    auto *child = boundary_.query(*children[i], 1282304865U);
    if (!child)
      continue;

    // The source port keeps borrowed children independently of CCL ownership.
    // Compare their actual CCL component names as Component::findChild does.
    const Core::ConstString name(child->state_.component.getName());
    for (std::size_t j = 0; j < partner.state_.count; ++j) {
      auto *candidate = partner.state_.children[j];
      if (candidate && candidate->state_.component.getName() == name) {
        if (auto *other = partner.boundary_.query(*candidate, 1282304865U))
          child->linkAsMaster(*other);
        break;
      }
    }
  }
}

void LinkableComponent::setLink(LinkableComponent &partner, bool inverse) {
  if (state_.partner == &partner)
    return;
  if (inverse)
    boundary_.set(partner, *this, false);
  else
    boundary_.master(*this, partner);
}
void LinkableComponent::removeLink() {
  if (!state_.partner)
    return;
  auto *partner = state_.partner;
  state_.partner = nullptr;
  boundary_.remove(*partner);
  // Native snapshots the child array and count after partner removal.
  auto *children = state_.children;
  auto count = state_.count;
  for (std::size_t i = 0; i < count; ++i)
    if (children[i])
      if (auto *child = boundary_.query(*children[i], 1282304865U))
        boundary_.remove(*child);
  state_.slave = 0;
}
void LinkableComponent::setLinkEnabled(bool enabled) {
  // Native snapshots count before writing enabled, then obtains child array.
  auto count = state_.count;
  state_.enabled = enabled;
  auto *children = state_.children;
  for (std::size_t i = 0; i < count; ++i)
    if (children[i])
      if (auto *child = boundary_.query(*children[i], 1282304865U))
        child->setLinkEnabled(enabled);
}
bool LinkableComponent::isLinked() const { return state_.partner != nullptr; }
std::uint8_t LinkableComponent::isLinkSlave() const { return state_.slave; }
LinkableComponent *LinkableComponent::castTo(int id) {
  return id == 1282304865 || id == 1400259439 || id == 1131375984 ? this
                                                                  : nullptr;
}
} // namespace Presonus
