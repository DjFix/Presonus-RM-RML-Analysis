#include "presonus/reconstruction200/large02_w01.hpp"
#include <cstdint>
#include <cstring>
#include <stdexcept>
namespace Presonus::Surface {
int SLMixerHandler::getCurrentMix() const {
  if (controller_) {
    int selected = controller_->getRadioValue(13, 33);
    if (selected >= 0)
      return selected;
  }
  return 33;
}
int SLMixerHandler::getSelectedBank() const {
  if (!controller_)
    return -1;
  // The native caller requires all seven mapping parameters to exist.
  for (int tag : {4, 5, 6, 0, 1, 2, 3}) {
    auto *parameter = getMappingParameter(tag);
    if (!parameter)
      throw std::logic_error("missing bank mapping parameter");
    if (parameter->getValue() > 0.f)
      return tag;
  }
  return -1;
}
void SLMixerHandler::onIdle() {
  if (!encoderTimer_.isLongEnoughYet())
    return;
  encoderTimer_.reset();
  if (!savedMeterMode_)
    return;
  std::uint32_t bits = static_cast<std::uint32_t>(savedMeterMode_) + 33U;
  int tag;
  std::memcpy(&tag, &bits, sizeof tag);
  if (auto *parameter = getMappingParameter(tag))
    parameter->setValue(1.f, true);
}
bool SLMixerHandler::showAutoGroups() const {
  if (!mappingState_)
    throw std::logic_error("SL mapping state is unbound");
  auto *parameter = mappingState_->parameters.byTag(10);
  return parameter && parameter->getValue() > 0.f;
}
bool SLMixerHandler::showPeakHold() const {
  if (!mappingState_)
    throw std::logic_error("SL mapping state is unbound");
  auto *parameter = mappingState_->parameters.byTag(9);
  return parameter && parameter->getValue() > 0.f;
}
bool SLMixerHandler::isValidGroup(Core::Portable::Component *component) const {
  if (!component)
    return false;
  auto *parameter = component->getParameterByTag(600);
  if (!parameter)
    return false;
  char text[32] = {};
  parameter->toString(text, sizeof text);
  return std::strlen(text) > 0;
}
void SLMixerHandler::onModifiersChanged() {
  if (getSelectedBank() == 6)
    updateConnections();
  if (mappingState_ && mappingState_->mixer && mappingState_->hasSecondaryMixer)
    updateConnections();
}
Core::Portable::Component *SLMixerHandler::getSelectedGeq() const {
  if (!mappingState_ || !mappingState_->mixer)
    throw std::logic_error("selected GEQ requires a mixer binding");
  auto *parameter = mappingState_->parameters.byTag(2);
  if (!parameter)
    throw std::logic_error("missing selected GEQ parameter");
  // Defined source-port conversion domain: finite float representable by int.
  int selected = static_cast<int>(parameter->getValue());
  if (selected > 19)
    return mappingState_->mainGeqs[selected == 20 ? 0 : 1];
  if (selected >= mappingState_->busGeqs.count())
    return nullptr;
  return mappingState_->busGeqs.at(selected);
}
bool SLMixerHandler::getStripAssignData(StripAssignData &data) const {
  if (!controller_ || !mappingState_ || !mappingState_->mixer)
    return false;
  data.bankOffset = controller_->getBankScrollingOffset();
  data.mix = getCurrentMix();
  data.inputs = false;
  int bank = getSelectedBank();
  auto add = [&](int tag) { data.lists.add(mappingState_->banks[tag]); };
  if (bank == 5)
    add(4);
  else if (bank == 4) {
    add(2);
    add(3);
    add(1);
  } else if (bank == 6) {
    if (!mappingState_->groups)
      throw std::logic_error("group tree is unbound");
    data.lists.add(mappingState_->groups->findChild("filtergroup"));
    if (showAutoGroups())
      data.lists.add(mappingState_->groups->findChild("autofiltergroup"));
  } else {
    add(0);
    if (mappingState_->secondaryInputs)
      data.lists.add(mappingState_->secondaryInputs);
    if (mappingState_->hasSecondaryMixer) {
      add(2);
      add(1);
    }
    data.inputs = true;
  }
  return true;
}
void SLMixerHandler::getChannelPanAndLinkParams(
    Core::Portable::Component &channel, Core::Portable::Parameter **pan,
    Core::Portable::Parameter **link) {
  if (getSelectedBank() == 4) {
    *pan = nullptr;
    *link = nullptr;
    return;
  }
  int mix = getCurrentMix();
  *link = channel.getParameterByTag(21);
  bool linked = *link && (*link)->getValue() > 0.f;
  auto index = static_cast<std::uint32_t>(mix) - 13U;
  bool isBus = index <= 15U;
  Core::Portable::Component *bus = nullptr;
  bool busMain = false;
  if (mappingState_ && mappingState_->mixer && isBus) {
    auto *list = mappingState_->banks[4];
    if (list) {
      bus = list->getChild(static_cast<int>(index));
      if (bus) {
        auto *parameter = bus->getParameterByTag(411);
        busMain = parameter && parameter->getValue() > 0.f;
      }
    }
  }
  if (mix == 33 || busMain) {
    auto *parameter = channel.getParameterByTag(411);
    if (parameter && parameter->getValue() == 0.f) {
      *pan = nullptr;
      return;
    }
    *pan = channel.getParameterByTag(linked ? 20 : 19);
  } else if (isBus && bus) {
    auto *parameter = bus->getParameterByTag(21);
    if (parameter && parameter->getValue() > 0.f) {
      *pan = channel.getParameterByTag((linked ? 248 : 240) +
                                       static_cast<int>(index) / 2);
      *link = channel.getParameterByTag(21);
    }
  }
  // Native early paths leave the caller's existing pan unchanged.
}
int EQPageComponent::getEqEncoderMode() const {
  auto *parameter = encoderParameters_.byTag(1000);
  if (!parameter)
    throw std::logic_error("missing EQ encoder parameter");
  // Defined source-port float-to-int domain is finite and int-representable.
  return static_cast<int>(parameter->getValue());
}
int SLMixerHandler::getEqEncoderMode() const {
  return eqPage_ ? eqPage_->getEqEncoderMode() : 0;
}
void SLMixerHandler::onMappingParamChanged(
    Core::Portable::Parameter *parameter) {
  if (mappingState_ && mappingState_->mixer) {
    int tag = parameter->getTag();
    int bank = getSelectedBank();
    auto set = [&](Core::Portable::Parameter *p, float value, bool edit) {
      if (!p)
        throw std::logic_error("missing required mapping parameter");
      p->setValue(value, edit);
    };
    if (static_cast<std::uint32_t>(tag) - 34U <= 3U)
      mappingState_->meterModeTwo = getMeterMode() == 2;
    if (static_cast<std::uint32_t>(tag) - 13U <= 15U) {
      if (bank == 5)
        set(getMappingParameter(0), 1.f, true);
    } else if (static_cast<std::uint32_t>(tag) - 29U <= 3U) {
      set(mappingState_->parameters.byTag(1), static_cast<float>(tag) - 29.f,
          false);
      set(controller_->getMainScreenParamByTag(5), 1.f, true);
      if (bank == 4)
        set(getMappingParameter(0), 1.f, true);
    } else if (tag == 4) {
      for (int other = 29; other != 33; ++other) {
        auto *p = getMappingParameter(other);
        if (!p)
          throw std::logic_error("missing FX mapping parameter");
        if (p->getValue() > 0.f) {
          set(getMappingParameter(33), 1.f, true);
          break;
        }
      }
    }
  }
  updateConnections();
}
bool SLMixerHandler::handleMappingRadioGroup(
    Core::Portable::Parameter *parameter) {
  int tag = parameter->getTag();
  if (static_cast<std::uint32_t>(tag) > 6U)
    return false;
  auto *groups = getMappingParameter(6);
  auto *buses = getMappingParameter(5);
  if (!groups || !buses || !controller_)
    throw std::logic_error("unbound radio mapping");
  float oldGroups = groups->getValue();
  if (mappingState_ && mappingState_->mixer &&
      mappingState_->hasSecondaryMixer && mappingState_->bankSwitchBlocked &&
      parameter->getValue() == 0.f) {
    controller_->setRadioGroup(-1, 0, 6, false);
  } else if (tag == 6 && groups->getValue() < .5f) {
    controller_->setRadioGroup(0, 0, tag, false);
  } else if (parameter == buses && parameter->getValue() < .5f) {
    controller_->setRadioGroup(0, 0, 6, false);
  } else if (parameter->getValue() > 0.f) {
    controller_->setRadioGroup(tag, 0, 6, false);
  }
  if (oldGroups > 0.f) {
    if (!mappingState_ || !mappingState_->mappingTable)
      throw std::logic_error("radio colors require MappingTable");
    for (int index = 1; index <= 16; ++index) {
      Core::CStringBuffer<32> name(nullptr);
      name.appendFormat("%s_%02d", "strip_select", index);
      mappingState_->mappingTable->setControlColor(name.str(), "coral");
    }
  }
  return true;
}
void SLMixerHandler::updateSelectedMix(const StripAssignData &data) {
  if (!mappingState_ || !mappingState_->mixer)
    throw std::logic_error("selected mix requires actual mixer state");
  auto &state = *mappingState_;
  int mix = data.mix;
  int selected;
  if (mix == 33) {
    if (!state.mappingTable)
      throw std::logic_error("selected main mix requires MappingTable");
    auto *p = state.mappingTable->getHardwareParameter("mono_select");
    selected = p && p->getValue() > 0.f ? 21 : 20;
  } else {
    std::uint32_t bits = static_cast<std::uint32_t>(mix) - 13U;
    std::memcpy(&selected, &bits, sizeof selected);
    if (bits <= 15U) {
      auto *list = state.banks[4];
      auto *bus = list ? list->getChild(selected) : nullptr;
      auto *linked = bus ? bus->getParameterByTag(21) : nullptr;
      if (linked) {
        float value = linked->getValue();
        auto *other = getMappingParameter((selected & 1) ? mix - 1 : mix + 1);
        if (other)
          other->setValue(value > 0.f ? 1.f : 0.f, false);
      }
    }
  }
  auto required = [&](int tag) {
    auto *p = state.parameters.byTag(tag);
    if (!p)
      throw std::logic_error("missing selected mix local parameter");
    return p;
  };
  required(2)->setValue(static_cast<float>(selected), true);
  int count = state.busGeqs.count();
  Core::CStringBuffer<64> name(nullptr);
  bool valid;
  if (selected <= 19) {
    valid = count > selected;
    auto *list = state.banks[4];
    auto *bus = list ? list->getChild(selected) : nullptr;
    auto *username = bus ? bus->findParameter("username") : nullptr;
    if (username) {
      char buffer[64]{};
      username->toString(buffer, 64);
      name = buffer;
    }
  } else {
    name = selected == 20 ? "Main L/R" : "Main Center";
    valid = true;
  }
  required(3)->fromString(name.str(), true);
  required(4)->setValue(valid ? 1.f : 0.f, true);
  Core::CString256 message(nullptr);
  if (!valid)
    message.appendFormat("To access GEQ, select Mix Bus 1-%d or the Main Mix.",
                         count);
  required(5)->fromString(message.str(), true);
}
} // namespace Presonus::Surface
