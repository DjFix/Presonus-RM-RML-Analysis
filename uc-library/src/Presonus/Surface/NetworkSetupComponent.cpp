#include "presonus/surface/NetworkSetupComponent.hpp"
#include "core/portable/corepersistence.h"
#include "core/system/coredebug.h"
#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/surface/RadioToggleButton.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include <cstring>
namespace presonus::surface {
int SurfaceNetworkProvider::localAddresses(Core::Sockets::IPAddress *list,
                                           int capacity) const {
  return Core::Sockets::Network::getLocalIPAddressList(list, capacity);
}
bool SurfaceNetworkProvider::parseAddress(Core::Sockets::SocketAddress &address,
                                          const char *text) const {
  return Core::Sockets::Network::getAddressFromString(address, text);
}
} // namespace presonus::surface
namespace Presonus::Surface {
NetworkSetupComponent::~NetworkSetupComponent() {
  if (ownedModel_ && state_.model == ownedModel_.get())
    state_.model = nullptr;
}
void *NetworkSetupComponent::castTo(Core::Portable::ITypedObject::TypeID id) {
  if (id == Core::Portable::ViewController::kTypeID)
    return static_cast<Core::Portable::ViewController *>(this);
  return Core::Portable::Component::castTo(id);
}
Core::Portable::Parameter *
NetworkSetupComponent::findParameter(const char *name) const {
  if (auto *p = Core::Portable::Component::findParameter(name))
    return p;
  return state_.parameters.findParameter(name);
}
Core::Portable::View *NetworkSetupComponent::createView(const char *type) {
  if (std::strcmp(type ? type : "", "RadioToggleButton") == 0)
    return new RadioToggleButton;
  return Core::Portable::ComponentViewController<
      NetworkSetupComponent>::createView(type);
}
void *NetworkSetupComponent::getObjectForView(const char *name,
                                              const char *type) {
  if (std::strcmp(type ? type : "", "ListModel") == 0 &&
      std::strcmp(name ? name : "", "networkList") == 0) {
    if (!state_.model) {
      ownedModel_ = std::make_unique<ListModel>(this);
      state_.model = ownedModel_.get();
      setupListModel();
    }
    return state_.model;
  }
  return Core::Portable::ComponentViewController<
      NetworkSetupComponent>::getObjectForView(name, type);
}
void NetworkSetupComponent::ListModel::setSelected(UC::NetworkItem *item) {
  const int count = views.count();
  setSelectedItem(item);
  for (int i = 0; i < count; ++i)
    views[i]->makeSelectedItemVisible();
}

void NetworkSetupComponent::syncListParam(
    int tag, const Core::Vector<UC::NetworkItem *> &items,
    UC::NetworkItem *selected) const {
  auto *p =
      Core::Portable::ListParam::cast(state_.parameters.getParameterByTag(tag));
  p->removeAll();
  p->appendString("None");
  const int mappings = tag == 7 ? state_.dependencies.mappingCount() : 0;
  for (int i = 0; i < mappings; ++i)
    p->appendString(state_.dependencies.mappingName(i));
  for (int i = 0; i < items.count(); ++i) {
    Core::CStringBuffer<128> text;
    state_.dependencies.title(*items[i], text);
    p->appendString(text);
  }
  const int value = selected   ? mappings + 1 + items.index(selected)
                    : tag == 7 ? state_.selectedMidiMapping + 1
                               : 0;
  p->setValue(static_cast<float>(value), false);
  p->rangeChanged();
}
void NetworkSetupComponent::onNetworkItemAdded(UC::NetworkItem *item) {
  Core::Sockets::IPAddress addresses[2];
  const int count = state_.network.localAddresses(addresses, 2);
  if (count == 0) {
    state_.adaptorConfigPending = true;
    return;
  }
  bool assigned = true;
  for (int i = count - 1; i >= 0; --i)
    if (addresses[i].ip.address[0] == 0)
      assigned = false;
  auto &d = state_.dependencies;
  const int type = d.kind(*item);
  if (type == 0) {
    bool found = false;
    for (int i = 0; i < state_.mixers.count(); ++i)
      if (d.associatedItem(*state_.mixers[i]) == item) {
        found = true;
        break;
      }
    if (!found) {
      state_.mixers.add(item);
      syncListParam(0, state_.mixers, state_.selectedMixer);
      if (assigned && !state_.selectedMixer && d.stored("selectedMixer", item))
        state_.parameters.getParameterByTag(0)->setValue(
            static_cast<float>(state_.mixers.index(item) + 1), true);
    }
  } else if (type == 1) {
    state_.daws.add(item);
    syncListParam(7, state_.daws, state_.selectedDAW);
    if (assigned && !state_.selectedDAW && d.stored("selectedDAW", item)) {
      const int index = state_.daws.index(item);
      const int mappings = d.mappingCount();
      state_.parameters.getParameterByTag(7)->setValue(
          static_cast<float>(mappings + index + 1), true);
    }
  }
  if (d.targetType() == d.kind(*item))
    setupListModel();
}
void NetworkSetupComponent::selectMixer(UC::NetworkItem *item, int flags) {
  if (item == state_.selectedMixer)
    return;
  auto &d = state_.dependencies;
  if (state_.selectedMixer) {
    d.setMixer(nullptr);
    d.release(state_.selectedMixer, (flags & 1) != 0);
  }
  state_.selectedMixer = item;
  if (item) {
    d.acquire(item);
    auto *c = d.component(state_.selectedMixer);
    d.setMixer(c ? d.mixerCast(c) : nullptr);
  }
  d.itemInfo(0, state_.selectedMixer);
  d.storeSelected("selectedMixer", state_.selectedMixer, flags);
  d.setNetworkRoot(getRootComponent());
}
void NetworkSetupComponent::selectDAW(UC::NetworkItem *item, int flags) {
  auto &d = state_.dependencies;
  if (item != state_.selectedDAW) {
    if (state_.selectedDAW) {
      d.setDAW(nullptr);
      d.setTransport(nullptr);
      d.release(state_.selectedDAW, (flags & 1) != 0);
    }
    state_.selectedDAW = item;
    if (item) {
      d.acquire(item);
      auto *c = d.component(state_.selectedDAW);
      auto *daw = c ? d.dawCast(c) : nullptr;
      d.setDAW(daw);
      d.setTransport(daw);
    }
  }
  d.itemInfo(1, item);
}
void NetworkSetupComponent::setupListModel() {
  if (!state_.model)
    return;
  const bool mixer = state_.dependencies.targetType() == 0;
  const auto &items = mixer ? state_.mixers : state_.daws;
  auto *selected = mixer ? state_.selectedMixer : state_.selectedDAW;
  state_.model->removeAll();
  state_.model->addItem(new Core::Portable::ListViewItem("None"));
  for (int i = 0; i < items.count(); ++i) {
    Core::CStringBuffer<128> text;
    state_.dependencies.title(*items[i], text);
    auto *row = new Core::Portable::ListViewItem(text);
    row->setUserData(items[i]);
    state_.model->addItem(row);
  }
  state_.model->changed();
  state_.dependencies.selectModelItem(selected);
}
void NetworkSetupComponent::adaptorConfigChanged(
    const Presonus::WIFIManager &) {
  if (state_.adaptorConfigPending)
    state_.dependencies.enableNetwork(true);
  state_.adaptorConfigPending = false;
  Core::DebugPrintf("UCNET: un-suspending network adaptors\n");
  state_.dependencies.resumeAdaptors();
  state_.dependencies.setupLocalIP();
}
void NetworkSetupComponent::onIdle() {
  Core::Portable::Component::onIdle();
  if (!state_.timer.isLongEnoughYet())
    return;
  state_.timer.reset();
  if (state_.dependencies.wiredAssignMode() != 0)
    state_.dependencies.configureNetwork("-a");
  else {
    Core::DebugPrintf("UCNET: un-suspending network adaptors\n");
    state_.dependencies.resumeAdaptors();
  }
}
void NetworkSetupComponent::onNetworkShutdown() {
  selectMixer(nullptr, 1);
  selectDAW(nullptr, 1);
}
void NetworkSetupComponent::onNetworkItemRemoved(UC::NetworkItem *item) {
  if (item == state_.selectedMixer)
    selectMixer(nullptr, 0);
  else if (item == state_.selectedDAW)
    selectDAW(nullptr, 0);
  const int kind = state_.dependencies.kind(*item);
  if (kind == 0) {
    state_.mixers.remove(item);
    syncListParam(0, state_.mixers, state_.selectedMixer);
  } else if (kind == 1) {
    state_.daws.remove(item);
    syncListParam(7, state_.daws, state_.selectedDAW);
  }
  if (state_.dependencies.targetType() == state_.dependencies.kind(*item))
    setupListModel();
}
void NetworkSetupComponent::setupNetworkInfo() {
  Core::CStringBuffer<128> text;
  auto *item = state_.selectedMixer ? state_.selectedMixer : state_.selectedDAW;
  if (item) {
    Core::Sockets::IPAddress address;
    if (state_.network.parseAddress(address, state_.dependencies.host(*item)))
      text = "Connected";
  } else
    text = "Not Connected";
  state_.parameters.getParameterByTag(29)->fromString(text, false);
}
void NetworkSetupComponent::loadSettings() {
  for (int i = 0; i < state_.midiHandler->countMappings(); ++i) {
    if (!isStoredItem("selectedDAW", i))
      continue;
    state_.selectedMidiMapping = i;
    state_.parameters.getParameterByTag(7)->setValue(
        static_cast<float>(i) + 1.f, true);
    state_.midiHandler->setActiveMapping(i);
    if (auto *p = state_.parameters.getParameterByTag(17))
      p->setValue(1.f, false);
    break;
  }
  syncListParam(7, state_.daws, nullptr);
}
void NetworkSetupComponent::storeSelected(const char *key,
                                          UC::NetworkItem *item, int flags) {
  if (!(flags & 2))
    return;
  Core::CStringBuffer<64> text;
  if (item)
    text = item->portableIdentity();
  auto &settings = state_.settings ? *state_.settings
                                   : Core::Portable::SettingFile::instance();
  settings.getSection(state_.settingsSection).set(key, text);
  settings.setDirty();
}
bool NetworkSetupComponent::isStoredItem(const char *key,
                                         UC::NetworkItem *item) const {
  auto &settings = state_.settings ? *state_.settings
                                   : Core::Portable::SettingFile::instance();
  Core::CStringBuffer<64> saved(
      settings.getSection(state_.settingsSection).getString(key));
  return saved[0] && std::strcmp(item->portableIdentity(), saved) == 0;
}
void NetworkSetupComponent::storeSelected(const char *key, int index,
                                          int flags) {
  if (!(flags & 2))
    return;
  Core::CStringBuffer<64> text;
  text.appendFormat("MIDI-%d", index);
  auto &settings = state_.settings ? *state_.settings
                                   : Core::Portable::SettingFile::instance();
  settings.getSection(state_.settingsSection).set(key, text);
  settings.setDirty();
}
bool NetworkSetupComponent::isStoredItem(const char *key, int index) const {
  auto &settings = state_.settings ? *state_.settings
                                   : Core::Portable::SettingFile::instance();
  Core::CStringBuffer<64> saved(
      settings.getSection(state_.settingsSection).getString(key));
  Core::CStringBuffer<64> text;
  text.appendFormat("MIDI-%d", index);
  return saved[0] && std::strcmp(text, saved) == 0;
}
Core::Portable::Parameter *NetworkSetupComponent::getSelectedMixerParam() {
  return state_.parameters.getParameterByTag(0);
}
int NetworkSetupComponent::getTargetType() const {
  return static_cast<int>(
             state_.parameters.getParameterByTag(30)->getValue()) != 0;
}
int NetworkSetupComponent::getWiredNetworkAssignMode() const {
  auto *p = state_.parameters.getParameterByTag(24);
  return p ? static_cast<int>(p->getValue()) : 0;
}
} // namespace Presonus::Surface
