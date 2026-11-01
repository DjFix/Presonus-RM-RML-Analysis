#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>
namespace presonus::surface {
// Independent source-port state, not the original ARM object layout.
struct PresetEntry {
  std::uint32_t identity;
  Core::CString128 name;
};
struct PresetsPageState {
  int category = 0;
  int rows = 1;
  int offset = 0;
  int selected = -1;
  bool mixer = false;
  Core::Portable::Component &parameters;
};
// Required app boundaries; no production no-op providers. Pointers and strings
// returned here are borrowed for the duration of the synchronous operation.
struct PresetsPageDependencies {
  virtual ~PresetsPageDependencies() = default;
  virtual bool handlerAvailable() = 0;
  virtual int count(int category) = 0;
  virtual const PresetEntry *preset(int category, int index) = 0;
  virtual void reload(int category) = 0;
  virtual void defaultName(int category, Core::CString128 &) = 0;
  virtual void categoryName(int category, Core::CString128 &) = 0;
  virtual const char *emptyMarker() = 0;
  virtual void baseShow(bool) = 0;
  virtual bool visible() = 0;
  virtual void connect(const char *, Core::Portable::Parameter *) = 0;
  virtual void recallOptions(Core::CString256 &) = 0;
  virtual void recall(const PresetEntry *, int, const Core::CString256 &) = 0;
  virtual void remove(const PresetEntry *, int) = 0;
  virtual void store() = 0;
  virtual void startTextInput(Core::Portable::Parameter *, const char *) = 0;
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Partial original scope. Return declarations, bases, lifecycle and layout are
// unresolved; this explicit source-port constructor claims no original symbol.
class PresetsPageComponent {
public:
  PresetsPageComponent(presonus::surface::PresetsPageState &state,
                       presonus::surface::PresetsPageDependencies &dependencies)
      : state(state), dependencies(dependencies) {}
  const presonus::surface::PresetEntry *getSelectedPreset() const;
  void onShow(bool);
  int getMaxListOffset() const;
  void textInputFinished(bool);
  void addListOffset(int);
  void recall();
  void promptToStore();
  void updatePresets();
  void remove();
  void onObjectChanged(Presonus::IMixerComponentObserver::ObjectChangeMessage);

private:
  presonus::surface::PresetsPageState &state;
  presonus::surface::PresetsPageDependencies &dependencies;
};
} // namespace Presonus::Surface
