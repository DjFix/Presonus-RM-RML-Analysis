#include "presonus/mixer/GlobalComponent.hpp"
namespace Presonus::Mixer {
namespace {
// RM 13731 literal-bound 0x176ba8 table; host pointer relocation is
// intentional. Static metadata and strings outlive the CCL factory-owned
// parameters.
Core::CStringPtr globalStrings4[] = {"Master", "Slave 1"};
Core::CStringPtr globalStrings5[] = {"Unlinked", "Linked-Master",
                                     "Linked-Slave"};
Core::CStringPtr globalStrings6[] = {"No Driver", "Driver On"};
Core::CStringPtr globalStrings7[] = {"No", "Yes"};
Core::CStringPtr globalStrings8[] = {"No", "Yes"};
Core::CStringPtr globalStrings9[] = {"No", "Yes"};
Core::CStringPtr globalStrings10[] = {"No", "Yes"};
Core::CStringPtr globalStrings11[] = {"No", "Yes"};
Core::CStringPtr globalStrings12[] = {"No", "Yes"};
Core::CStringPtr globalStrings13[] = {"No", "Yes"};
Core::CStringPtr globalStrings14[] = {"No", "Yes"};
Core::CStringPtr globalStrings15[] = {"No", "Yes"};
Core::CStringPtr globalStrings16[] = {"No", "Yes"};
Core::CStringPtr globalStrings17[] = {"-6dB/8va", "-12dB/8va", "-24dB/8va"};
Core::CStringPtr globalStrings19[] = {"Off", "On"};
Core::CStringPtr globalStrings20[] = {"44.1 kHz", "48 kHz", "88.2 kHz",
                                      "96 kHz"};
Core::CStringPtr globalStrings25[] = {"No", "Yes"};
Core::CStringPtr globalStrings28[] = {"No", "Yes"};
Core::CStringPtr globalStrings30[] = {"No", "Yes"};
Core::CStringPtr globalStrings36[] = {"Unlocked", "Locked"};
Core::CStringPtr globalStrings37[] = {"No", "Yes"};
Core::CStringPtr globalStrings38[] = {"No", "Yes"};
Core::CStringPtr globalStrings39[] = {"No", "Yes"};
Core::CStringPtr globalStrings40[] = {"No", "Yes"};
Core::CStringPtr globalStrings43[] = {"Master", "Slave"};
Core::CStringPtr globalStrings44[] = {"No", "Yes"};
Core::CStringPtr globalStrings45[] = {"LR", "LCR"};
Core::CStringPtr globalStrings46[] = {"No", "Yes"};
Core::CStringPtr globalStrings47[] = {"No", "Yes"};
Core::CStringPtr globalStrings48[] = {"No", "Yes"};
Core::CStringPtr globalStrings49[] = {"Off", "On"};
Core::CStringPtr globalStrings50[] = {"Off", "On"};
const Core::Portable::ParamInfo globalParameterInfos[] = {
    {4, 0, "panelversion", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0, nullptr, nullptr,
     nullptr, "Panel Version", nullptr},
    {4, 1, "dspversion", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0, nullptr, nullptr,
     nullptr, "DSP Version", nullptr},
    {4, 2, "fpgaversion", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0, nullptr, nullptr,
     nullptr, "FPGA Version", nullptr},
    {0, 3, "clip", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, "", nullptr, nullptr,
     "Clip", nullptr},
    {2, 4, "chainid", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings4, "Chain ID", nullptr},
    {2, 5, "linkstate", 0.0f, 2.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     globalStrings5, "Link State", nullptr},
    {2, 6, "driverstate", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     globalStrings6, "Driver State", nullptr},
    {2, 7, "fltrmute", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings7, "Recall Mute", nullptr},
    {2, 8, "fltrfx", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings8, "Recall FX", nullptr},
    {2, 9, "fltraux", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings9, "Recall Aux Mix", nullptr},
    {2, 10, "fltrfader", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings10, "Recall Faders", nullptr},
    {2, 11, "fltrassign", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings11, "Recall Assign", nullptr},
    {2, 12, "fltrpots", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings12, "Recall Pots", nullptr},
    {2, 13, "fltreqdyn", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings13, "Recall EQ Dyn", nullptr},
    {2, 14, "fltrgeq", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings14, "Recall GEQ", nullptr},
    {2, 15, "fltrname", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings15, "Recall User Name", nullptr},
    {2, 16, "fltrdcagrp", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings16, "Recall DCA group", nullptr},
    {2, 17, "hpfslope", 0.0f, 2.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings17, "HiPass Slope", nullptr},
    {0, 18, "autostore", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, "", nullptr, nullptr,
     "Autostore notify", nullptr},
    {2, 19, "showPeakHold", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings19, "Show Peak Hold", nullptr},
    {2, 20, "samplerate", 0.0f, 3.0f, 0.0f, 1.0f, 1.0f, 18, nullptr, nullptr,
     globalStrings20, "Sample Rate", nullptr},
    {0, 21, "highdef", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, "", nullptr, nullptr,
     "High Definition", nullptr},
    {0, 22, "smaartwizardactive", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, "", nullptr,
     nullptr, "Smaart Wizard Active", nullptr},
    {0, 23, "spectrum_geq_active", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, "", nullptr,
     nullptr, "Spectrum GEQ Active", nullptr},
    {0, 24, "spectrum_fat_active", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, "", nullptr,
     nullptr, "Spectrum Fat Active", nullptr},
    {2, 25, "fader_locate", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     globalStrings25, "Fader Locate", nullptr},
    {0, 26, "lcdbacklight", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 6, "lowhigh", nullptr,
     nullptr, "Lcd Backlight", nullptr},
    {1, 27, "lcdcontrast", 0.0f, 20.0f, 0.0f, 12.0f, 1.0f, 6, "", "", nullptr,
     "Lcd Contrast", nullptr},
    {2, 28, "auxmutemode", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings28, "Aux Mute Mode", nullptr},
    {0, 29, "panic_muteall", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, "", nullptr,
     nullptr, "Mute All", nullptr},
    {2, 30, "lockable", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings30, "Mixer is Lockable", nullptr},
    {1, 31, "lockcode1", 0.0f, 9.0f, 0.0f, 0.0f, 1.0f, 2, "", "", nullptr,
     "lock code 1", nullptr},
    {1, 32, "lockcode2", 0.0f, 9.0f, 0.0f, 0.0f, 1.0f, 2, "", "", nullptr,
     "lock code 2", nullptr},
    {1, 33, "lockcode3", 0.0f, 9.0f, 0.0f, 0.0f, 1.0f, 2, "", "", nullptr,
     "lock code 3", nullptr},
    {1, 34, "lockcode4", 0.0f, 9.0f, 0.0f, 0.0f, 1.0f, 2, "", "", nullptr,
     "lock code 4", nullptr},
    {1, 35, "lockcode5", 0.0f, 9.0f, 0.0f, 0.0f, 1.0f, 2, "", "", nullptr,
     "lock code 5", nullptr},
    {2, 36, "lockstate", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings36, "Lock State", nullptr},
    {2, 37, "lockmasters", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings37, "Lock Masters", nullptr},
    {2, 38, "lockfaders", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings38, "Lock Faders", nullptr},
    {2, 39, "lockauxmix", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings39, "Lock AuxMix", nullptr},
    {2, 40, "lockscene", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings40, "Lock Scene", nullptr},
    {4, 41, "loaded_scene_name", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0, nullptr,
     nullptr, nullptr, "Loaded Scene", nullptr},
    {4, 42, "loaded_scene_title", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0, nullptr,
     nullptr, nullptr, "Loaded Scene", nullptr},
    {2, 43, "link_id", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings43, "link_id", nullptr},
    {2, 44, "subgroupmerge", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings44, "Subgroup merge", nullptr},
    {2, 45, "panmode", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr, nullptr,
     globalStrings45, "Pan Mode", nullptr},
    {2, 46, "fltr_cheq", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 0, nullptr, nullptr,
     globalStrings46, "Recall Channel EQ", nullptr},
    {2, 47, "fltr_chgate", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 0, nullptr, nullptr,
     globalStrings47, "Recall Channel Gate", nullptr},
    {2, 48, "fltr_chcomp", 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 0, nullptr, nullptr,
     globalStrings48, "Recall Channel Comp", nullptr},
    {2, 49, "stagebox_onoff", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 128, nullptr,
     nullptr, globalStrings49, "Stagebox OnOff", nullptr},
    {2, 50, "storedstagebox_on", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 2, nullptr,
     nullptr, globalStrings50, "Stored Stagebox OnOff", nullptr},
    {4, 51, "storedstagebox_mixer", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 2, nullptr,
     nullptr, nullptr, "Last Connected Mixer", nullptr},
    {4, 52, "storedcascade_slave", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 2, nullptr,
     nullptr, nullptr, "Last AVB Slave Mixer", nullptr},
};
static_assert(sizeof(globalParameterInfos) / sizeof(globalParameterInfos[0]) ==
              53);
} // namespace
GlobalComponent::GlobalComponent(MixerComponentBase &mixer)
    : Core::Portable::Component("global"), mixer_(&mixer) {
  // Source-port adaptation of the observed Server constructor feedback flag.
  // This does not establish original Server inheritance or ARM layout.
  paramList.setFeedbackNeeded(true);
  paramList.add(globalParameterInfos, 53, false);
  highDefSource_ =
      static_cast<Core::Portable::NumericParam *>(paramList.byTag(20));
  highDefDestination_ =
      static_cast<Core::Portable::NumericParam *>(paramList.byTag(21));
}
} // namespace Presonus::Mixer
#include "presonus/mixer/GlobalComponent.hpp"
namespace Presonus::Mixer {
GlobalComponent::~GlobalComponent() = default;
} // namespace Presonus::Mixer

#include "presonus/mixer/GlobalComponent.hpp"
#include <stdexcept>
namespace Presonus::Mixer {
Core::Portable::FileName GlobalComponent::getTempFilePath() {
  if (!mixer_)
    throw std::logic_error("GlobalComponent requires a live mixer binding");
  auto path = mixer_->getDataDir("temp");
  path.descend("mixer.scene");
  return path;
}
} // namespace Presonus::Mixer

namespace Presonus::Mixer {
void GlobalComponent::updateHighDef() {
  if (!highDefDestination_ || !highDefSource_)
    return;
  highDefDestination_->setValue(
      highDefSource_->getValue() >= 2.0f ? 1.0f : 0.0f, true);
}
} // namespace Presonus::Mixer

namespace Presonus::Mixer {
void GlobalComponent::initalize() {
  if (highDefSource_ && highDefDestination_)
    updateHighDef();
}
} // namespace Presonus::Mixer

#include "core/portable/corepersistence.h"
namespace Presonus::Mixer {
void GlobalComponent::storeMixerState(Core::Portable::IStorageFilter *filter) {
  if (!mixerStorage_)
    throw std::logic_error("Global store requires real mixer storage binding");
  using namespace Core::Portable;
  Attributes attributes(AttributeAllocator::getDefault());
  AttributesBuilder builder(attributes, true);
  OutputStorage storage(builder, filter);
  mixerStorage_->save(storage);
  const auto path = getTempFilePath();
  ArchiveUtils::saveInBackground(path.str(), attributes, nullptr,
                                 static_cast<Archiver::Format>(0),
                                 static_cast<FileStorageContext::Mode>(0), 0);
}
} // namespace Presonus::Mixer
