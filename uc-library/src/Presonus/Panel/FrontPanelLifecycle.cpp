#include "core/portable/coreattributes.h"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelComponent.hpp"

namespace presonus::frontpanel_port {
static void addNativeParameters(Core::Portable::Component &);
}

namespace Presonus::Panel {
// Exact native app table adaptation is supplied below once pointer data is
// bound.

struct FrontPanelComponent::Owned {
  Core::Vector<Core::Portable::NumericParam *> selectParameters;
  Core::Vector<Core::Portable::NumericParam *> mixParameters;
  Core::Portable::Attributes attributes;
  Presonus::DelayTimer timer{1.f};
  presonus::frontpanel_port::State state;
  explicit Owned(Core::Portable::Component &component)
      : attributes(Core::Portable::AttributeAllocator::getDefault()),
        state(component) {
    state.panelParameters = &component;
    state.copyContext = &attributes;
  }
};
FrontPanelComponent::FrontPanelComponent(
    presonus::frontpanel_port::State &s,
    presonus::frontpanel_port::Dependencies &d)
    : state(s), dependencies(checkedDependencies) {
  bindDependencies(d);
}
FrontPanelComponent::FrontPanelComponent(Presonus::Mixer::MixerComponentBase &m,
                                         PanelRegistrar &r)
    : PanelComponent(m, r),
      owned(std::make_unique<Owned>(portableState().component)),
      state(owned->state), dependencies(checkedDependencies) {
  presonus::frontpanel_port::addNativeParameters(portableState().component);
}
FrontPanelComponent::~FrontPanelComponent() = default;

// Both selected callers pass false to native updateFatChannel(bool). Its
// independently bound false-only path just sets byte +0x168. This portable
// state adaptation does not recover or claim that unassigned full helper.
void FrontPanelComponent::linkChanged() { state.fatChannelDirty = true; }
void FrontPanelComponent::notifyStoring(bool storing) {
  if (!state.storingParameters)
    return;
  if (auto *p = state.storingParameters->getParameterByTag(8))
    p->setValue(storing ? 1.f : 0.f, false);
}
void FrontPanelComponent::doMix(int tag, float value) {
  if (value > 0.f) {
    for (int i = 0; i < state.mixSelections.count(); ++i)
      if (state.mixSelections[i]->getTag() == tag) {
        state.mixSelections[i]->changed();
        break;
      }
    for (int i = 0; i < state.mixSelections.count(); ++i)
      if (state.mixSelections[i]->getTag() != tag)
        state.mixSelections[i]->setValue(0.f, false);
  } else {
    for (int i = 0; i < state.mixSelections.count(); ++i)
      state.mixSelections[i]->setValue(0.f, false);
  }
  if (auto *p = state.panelParameters->getParameterByTag(1))
    p->setValue(1.f, true);
  state.fatChannelDirty = true;
}
int FrontPanelComponent::getMeterMode() {
  for (int i = 1; i <= 6; ++i)
    if (state.panelParameters->getParameterByTag(i)->getValue() > 0.f)
      return i - 1;
  return 0;
}
Presonus::Mixer::ChannelComponent *FrontPanelComponent::getMixModeChannel() {
  for (int i = 0; i < state.mixSelections.count(); ++i) {
    auto *p = state.mixSelections[i];
    if (!(p->getValue() > 0.f))
      continue;
    int tag = p->getTag();
    if (tag < 200)
      return nullptr;
    auto &channels = tag <= 213 ? state.auxChannels : state.fxChannels;
    if (!channels.count())
      return nullptr;
    const int index = tag - (tag <= 213 ? 200 : 214);
    return channels.at(index);
  }
  return nullptr;
}
} // namespace Presonus::Panel

// BEGIN APP PARAMETER ADAPTER
// App data source port from two exact hash-verified tables. Host ParamInfo
// follows pinned CCL source; this is not the original ARM record layout.
namespace presonus::frontpanel_port::parameter_data {
using Core::Portable::ParamInfo;
static_assert(ParamInfo::kToggle == 0 && ParamInfo::kInt == 1 &&
              ParamInfo::kList == 2 && ParamInfo::kFloat == 3);
static const char *list_458180[] = {"Off", "On"};
static const char *list_458188[] = {"EFX A", "EFX B", "EFX C", "EFX D"};
static const char *list_458198[] = {"", "HD Mode engaged, EQ/Dyn Disabled.",
                                    "HD Mode engaged, Bus Disabled."};
static const char *list_4581a4[] = {"No", "Yes"};
// Native table 0x32690c, 134 records; SHA256
// a035e27477dab234265ac82551b71975bbb23f349c31bbd1cea314b210bbc0ef.
static const ParamInfo mainParameters[] = {
    {0, 1, "metermode_fat", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "metermode fat",
     nullptr},
    {0, 2, "metermode_input", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr,
     "metermode input", nullptr},
    {0, 3, "metermode_output", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr,
     "metermode output", nullptr},
    {0, 4, "metermode_gr", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "metermode gr",
     nullptr},
    {0, 5, "metermode_aux", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "metermode aux",
     nullptr},
    {0, 6, "metermode_locate", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr,
     "metermode locate", nullptr},
    {0, 7, "copy", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "copy", nullptr},
    {0, 8, "load", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "load", nullptr},
    {0, 9, "load_paste", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "Load Paste Mode",
     nullptr},
    {0, 10, "save", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "Save", nullptr},
    {2, 11, "merge", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, nullptr, nullptr, list_458180, "Sub Group Merge",
     nullptr},
    {1, 12, "metertype", 0x0.0p+0f, 0x1.8000000000000p+1f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", "", nullptr, "metertype", nullptr},
    {2, 13, "selfx", 0x0.0p+0f, 0x1.8000000000000p+1f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, nullptr, nullptr, list_458188, "Selected FX",
     nullptr},
    {0, 14, "key_listen", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "Key Listen",
     nullptr},
    {3, 15, "fader_pos_ch01", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 16, "fader_pos_ch02", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 17, "fader_pos_ch03", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 18, "fader_pos_ch04", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 19, "fader_pos_ch05", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 20, "fader_pos_ch06", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 21, "fader_pos_ch07", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 22, "fader_pos_ch08", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 23, "fader_pos_ch09", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 24, "fader_pos_ch10", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 25, "fader_pos_ch11", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 26, "fader_pos_ch12", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 27, "fader_pos_ch13", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 28, "fader_pos_ch14", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 29, "fader_pos_ch15", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 30, "fader_pos_ch16", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 31, "fader_pos_ch17", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 32, "fader_pos_ch18", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 33, "fader_pos_ch19", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 34, "fader_pos_ch20", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 35, "fader_pos_ch21", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 36, "fader_pos_ch22", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 37, "fader_pos_ch23", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 38, "fader_pos_ch24", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 39, "fader_pos_ch25", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 40, "fader_pos_ch26", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 41, "fader_pos_ch27", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 42, "fader_pos_ch28", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 43, "fader_pos_ch29", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 44, "fader_pos_ch30", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 45, "fader_pos_ch31", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 46, "fader_pos_ch32", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 47, "fader_pos_sub01", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 48, "fader_pos_sub02", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 49, "fader_pos_sub03", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 50, "fader_pos_sub04", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {3, 51, "fader_pos_main", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0624de0000000p-9f, 0, "", "", nullptr, "Fader Physical Pos",
     nullptr},
    {2, 52, "fatch_dspdark", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, nullptr, nullptr, list_458198,
     "Fat Ch DSP dark", nullptr},
    {0, 100, "select_ch01", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 101, "select_ch02", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 102, "select_ch03", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 103, "select_ch04", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 104, "select_ch05", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 105, "select_ch06", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 106, "select_ch07", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 107, "select_ch08", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 108, "select_ch09", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 109, "select_ch10", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 110, "select_ch11", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 111, "select_ch12", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 112, "select_ch13", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 113, "select_ch14", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 114, "select_ch15", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 115, "select_ch16", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 116, "select_ch17", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 117, "select_ch18", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 118, "select_ch19", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 119, "select_ch20", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 120, "select_ch21", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 121, "select_ch22", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 122, "select_ch23", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 123, "select_ch24", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 124, "select_ch25", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 125, "select_ch26", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 126, "select_ch27", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 127, "select_ch28", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 128, "select_ch29", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 129, "select_ch30", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 130, "select_ch31", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 131, "select_ch32", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 155, "select_auxina", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 156, "select_auxinb", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 199, "select_tapein", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 198, "select_digital", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 190, "select_fxreturna", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 191, "select_fxreturnb", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 192, "select_fxreturnc", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 193, "select_fxreturnd", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 132, "select_aux01", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 133, "select_aux02", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 134, "select_aux03", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 135, "select_aux04", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 136, "select_aux05", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 137, "select_aux06", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 138, "select_aux07", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 139, "select_aux08", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 140, "select_aux09", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 141, "select_aux10", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 142, "select_aux11", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 143, "select_aux12", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 144, "select_aux13", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 145, "select_aux14", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 151, "select_fxa", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 152, "select_fxb", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 153, "select_fxc", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 154, "select_fxd", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 146, "select_sub01", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 147, "select_sub02", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 148, "select_sub03", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 149, "select_sub04", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 150, "select_main", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {0, 194, "select_talkback", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", nullptr, nullptr, "select",
     nullptr},
    {1, 200, "mix_aux01", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 201, "mix_aux02", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 202, "mix_aux03", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 203, "mix_aux04", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 204, "mix_aux05", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 205, "mix_aux06", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 206, "mix_aux07", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 207, "mix_aux08", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 208, "mix_aux09", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 209, "mix_aux10", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 210, "mix_aux11", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 211, "mix_aux12", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 212, "mix_aux13", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 213, "mix_aux14", 0x0.0p+0f, 0x1.0000000000000p+1f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 214, "mix_fxa", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 215, "mix_fxb", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 216, "mix_fxc", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
    {1, 217, "mix_fxd", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, "", "", nullptr, "mix", nullptr},
};
// Native table 0x329504, 2 records; SHA256
// 83d97462eacc2cb98d40f992e56c4274ee971afacac8175b864e0ce0ff6ad2f3.
static const ParamInfo diagnosticParameters[] = {
    {2, 300, "all_leds_on", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f,
     0x0.0p+0f, 0x1.0000000000000p+0f, 0, nullptr, nullptr, list_458180,
     "All Leds On", nullptr},
    {2, 301, "dfutest", 0x0.0p+0f, 0x1.0000000000000p+0f, 0x0.0p+0f, 0x0.0p+0f,
     0x1.0000000000000p+0f, 0, nullptr, nullptr, list_4581a4, "DFU Test",
     nullptr},
};
} // namespace presonus::frontpanel_port::parameter_data
namespace presonus::frontpanel_port {
static void addNativeParameters(Core::Portable::Component &component) {
  using namespace parameter_data;
  component.addParameters(mainParameters, 134);
  component.addParameters(diagnosticParameters, 2);
}
} // namespace presonus::frontpanel_port
