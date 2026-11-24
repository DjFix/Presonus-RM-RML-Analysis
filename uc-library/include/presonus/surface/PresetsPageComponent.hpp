#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>
namespace Presonus {
class MixerClientComponentBase;
}
namespace presonus::surface {
// Independent source-port state, not the original ARM object layout.
struct PresetEntry {
  std::uint32_t identity;
  Core::CString128 name;
};
// Explicit source-port association; all pointers and vector are borrowed.
struct PresetsMixerBinding {
  Presonus::MixerClientComponentBase *mixer = nullptr;
  Core::Vector<Presonus::IMixerComponentObserver *> *observers = nullptr;
  Presonus::IMixerComponentObserver *pageObserver = nullptr;
};
struct PresetsPageState {
  int category = 0;
  int rows = 1;
  int offset = 0;
  int selected = -1;
  bool mixer = false;
  Core::Portable::Component &parameters;
  Presonus::IMappingController *mappingController = nullptr;
  Presonus::MixerClientComponentBase *mixerComponent = nullptr;
  Core::Vector<PresetsMixerBinding> *mixerBindings = nullptr;
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
class PresetsPageComponent : public Core::Portable::Component {
public:
  PresetsPageComponent(presonus::surface::PresetsPageState &state,
                       presonus::surface::PresetsPageDependencies &dependencies)
      : state(state), dependencies(dependencies) {}
  ~PresetsPageComponent() override;
  void setMixerComponent(Presonus::MixerClientComponentBase *);
  // Independent source-port vector: entries are borrowed, storage is owned.
  Core::Vector<Core::Portable::AliasParam *> &portableAliases() {
    return aliases_;
  }
  const presonus::surface::PresetEntry *getSelectedPreset() const;
  void setMappingController(Presonus::IMappingController *);
  void onShow(bool);
  void paramChanged(Core::Portable::Parameter *, int) override;
  // Native 16-byte body has stack setup/return only; intentional extension
  // hook.
  virtual void rowSelected();
  // Portable void member choice. The native hook leaves the buffer untouched;
  // its original return declaration and virtual dispatch remain unresolved.
  void getTargetUrl(Core::CStringBuffer<256> &);
  int getMaxListOffset() const;
  void textInputFinished(bool);
  void addListOffset(int);
  virtual void recall();
  void promptToStore();
  void updatePresets();
  virtual void remove();
  void onObjectChanged(Presonus::IMixerComponentObserver::ObjectChangeMessage);

private:
  Core::Vector<Core::Portable::AliasParam *> aliases_;
  presonus::surface::PresetsPageState &state;
  presonus::surface::PresetsPageDependencies &dependencies;
};
} // namespace Presonus::Surface
