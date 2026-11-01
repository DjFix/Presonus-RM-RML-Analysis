#include "presonus/surface/PresetsPageComponent.hpp"
#include <algorithm>
#include <cstring>
namespace {
int wrappingAdd(int a, int b) {
  return static_cast<std::int32_t>(static_cast<std::uint32_t>(a) +
                                   static_cast<std::uint32_t>(b));
}
} // namespace
namespace Presonus::Surface {
const presonus::surface::PresetEntry *
PresetsPageComponent::getSelectedPreset() const {
  if (!state.mixer || !dependencies.handlerAvailable() || state.selected < 0)
    return nullptr;
  dependencies.handlerAvailable();
  if (state.selected >= dependencies.count(state.category))
    return nullptr;
  dependencies.handlerAvailable();
  return dependencies.preset(state.category, state.selected);
}
int PresetsPageComponent::getMaxListOffset() const {
  if (!state.mixer || !dependencies.handlerAvailable())
    return 0;
  dependencies.handlerAvailable();
  const int count = dependencies.count(state.category);
  // Source-port domain requires a positive rows value. ARM division by zero and
  // signed overflow are outside the validated contract.
  const int offset = ((count - 1) / state.rows) * state.rows;
  return std::max(0, offset);
}
void PresetsPageComponent::textInputFinished(bool canceled) {
  if (!canceled)
    dependencies.store();
}
void PresetsPageComponent::addListOffset(int delta) {
  int next = wrappingAdd(state.offset, delta);
  next = next < 0 ? 0 : std::min(next, getMaxListOffset());
  if (next != state.offset) {
    state.offset = next;
    updatePresets();
  }
}
void PresetsPageComponent::recall() {
  if (!state.mixer)
    return;
  const auto *preset = getSelectedPreset();
  if (!preset)
    return;
  Core::CString256 options;
  dependencies.recallOptions(options);
  dependencies.recall(preset, state.category, options);
}
void PresetsPageComponent::remove() {
  if (!state.mixer)
    return;
  if (const auto *preset = getSelectedPreset())
    dependencies.remove(preset, state.category);
}
void PresetsPageComponent::promptToStore() {
  auto *parameter = state.parameters.getParameterByTag(1006);
  if (!parameter)
    return;
  const auto *preset = getSelectedPreset();
  if (!preset)
    return;
  Core::CString128 name(preset->name.str()), category;
  const char *marker = dependencies.emptyMarker();
  const char *found =
      name.isEmpty() ? nullptr : std::strstr(name.str(), marker ? marker : "");
  if (name.isEmpty() || found) {
    if (state.mixer && dependencies.handlerAvailable()) {
      dependencies.handlerAvailable();
      dependencies.defaultName(state.category, name);
      dependencies.handlerAvailable();
      dependencies.categoryName(state.category, category);
    }
  }
  parameter->fromString(name.str(), false);
  Core::CString128 title;
  title.appendFormat("%s Preset Name:", category.str());
  dependencies.startTextInput(parameter, title.str());
}
void PresetsPageComponent::updatePresets() {
  if (!dependencies.visible())
    return;
  Core::CString32 scratch;
  state.offset = std::min(state.offset, getMaxListOffset());
  for (int row = 0; row < state.rows; ++row) {
    auto *name = state.parameters.getParameterByTag(row * 3);
    auto *selected = state.parameters.getParameterByTag(row * 3 + 1);
    const int index = wrappingAdd(row, state.offset);
    const presonus::surface::PresetEntry *preset = nullptr;
    if (state.mixer && dependencies.handlerAvailable()) {
      dependencies.handlerAvailable();
      preset = dependencies.preset(state.category, index);
    }
    name->fromString(preset ? preset->name.str() : "", false);
    selected->setValue(state.selected == index ? 1.f : 0.f, false);
  }
}
void PresetsPageComponent::onShow(bool show) {
  dependencies.baseShow(show);
  if (dependencies.visible()) {
    state.selected = -1;
    if (state.mixer && dependencies.handlerAvailable()) {
      dependencies.handlerAvailable();
      dependencies.reload(state.category);
    }
    updatePresets();
  }
  auto *recall = dependencies.visible()
                     ? state.parameters.getParameterByTag(1004)
                     : nullptr;
  dependencies.connect("display_recall", recall);
  auto *store = dependencies.visible()
                    ? state.parameters.getParameterByTag(1005)
                    : nullptr;
  dependencies.connect("display_store", store);
}
void PresetsPageComponent::onObjectChanged(
    Presonus::IMixerComponentObserver::ObjectChangeMessage message) {
  constexpr int table[][2] = {{0, 0}, {1, 1}, {2, 2}, {3, 3}, {4, 4}, {10, 0}};
  for (const auto &entry : table)
    if (state.category == entry[0] && static_cast<int>(message) == entry[1]) {
      state.selected = -1;
      updatePresets();
      return;
    }
}
} // namespace Presonus::Surface
