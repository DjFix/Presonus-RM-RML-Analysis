#include "core/portable/corepersistence.h"
#include "core/portable/corestorage.h"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cmath>
#include <stdexcept>
namespace Presonus::Surface {
int SurfaceRootComponent::bumpFaderSpeed(int delta) {
  return registrar_ ? registrar_->bumpFaderSpeed(delta) : 0;
}
int SurfaceRootComponent::bumpFaderTouchSensitivity(int delta) {
  return registrar_ ? registrar_->bumpFaderTouchSensitivity(delta) : 0;
}
void SurfaceRootComponent::paramChangedLcdBrightness(
    Core::Portable::Parameter *parameter) {
  registrar_->adjustLcdBrightness(static_cast<int>(parameter->getValue()));
}
} // namespace Presonus::Surface

namespace Presonus::Surface {
void SurfaceRootComponent::updateFocusParams(
    Presonus::Panel::Control *control) {
  if (!control || !services_ || !services_->focus)
    return;
  auto *parameter = control->getParameter();
  if (!parameter)
    return;
  // Scope-safe source-port inlining of PageHeaderComponent::updateFocusParam,
  // original dependency symbol/range retained separately; no helper admission.
  auto &state = *services_->focus;
  if (!state.alias || !state.label)
    return;
  auto *original = parameter->getOriginal();
  if (!original || original == state.alias->getOriginal())
    return;
  if (!state.handlers)
    throw std::logic_error("live assignment handler list required");
  Presonus::MixerAssignmentHandler::FocusInfo info;
  // Scope-safe inlining of original AssignmentHandlerTable::getParamFocusInfo.
  // Original helper identities/ranges stay dependency evidence, never credits.
  const int count = state.handlers->count();
  bool found = false;
  for (int index = 0; index < count; ++index) {
    auto *handler = state.handlers->at(index);
    if (!handler)
      continue;
    auto *mixer = static_cast<Presonus::MixerAssignmentHandler *>(
        handler->castTo(0x4d784173));
    if (mixer && mixer->getParamFocusInfo(info, original)) {
      found = true;
      break;
    }
  }
  if (!found)
    return;
  state.alias->setOriginal(info.sourcePort.alternateOriginal
                               ? info.sourcePort.alternateOriginal
                               : original);
  state.label->fromString(info.sourcePort.label, false);
}
void SurfaceRootComponent::controlChanged(
    const Presonus::Panel::ControlRegistrar &, unsigned char, unsigned char *) {
}
void SurfaceRootComponent::faderChanged(
    const Presonus::Panel::ControlRegistrar &, int, int,
    Presonus::Panel::FaderControl *control) {
  updateFocusParams(control);
}
void SurfaceRootComponent::switchChanged(
    const Presonus::Panel::ControlRegistrar &, int, int, bool pressed,
    Presonus::Panel::SwitchControl *control) {
  if (pressed)
    updateFocusParams(control);
}
MainScreenComponent *SurfaceRootComponent::getMainScreenComponent() const {
  auto *component = services_->children->findChild("mainscreen");
  if (!component)
    return nullptr;
  for (const auto &reference : services_->mainScreens) {
    if (reference.component == component &&
        reference.elfSha256 == "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a"
                               "980d855ec5aa449a0" &&
        reference.nativeType ==
            "_ZTIN8Presonus7Surface19MainScreenComponentE" &&
        reference.nativeTypeAddress == 0x1a0434)
      return reference.reference;
  }
  return nullptr;
}
} // namespace Presonus::Surface

#include "core/system/coredebug.h"
#include <limits>
namespace Presonus::Surface {
void SurfaceRootComponent::terminateTestTouchscreen() {
  if (!services_)
    throw std::logic_error("root services required");
  services_->touchscreenActive = false;
  if (!services_->children)
    throw std::logic_error("live children required");
  auto *screen = getMainScreenComponent();
  Core::Portable::Component *component = nullptr;
  for (const auto &reference : services_->mainScreens)
    if (screen && reference.reference == screen &&
        reference.component == services_->children->findChild("mainscreen")) {
      component = reference.component;
      break;
    }
  if (!component || !services_->rootParameters || !services_->observer)
    throw std::logic_error("live root/screen parameters and observer required");
  auto *exit = component->getParameterByTag(38);
  if (!exit)
    throw std::logic_error("screen tag 38 required");
  exit->removeObserver(services_->observer);
  auto *touch = services_->rootParameters->getParameterByTag(903);
  if (!touch)
    throw std::logic_error("root tag 903 required");
  touch->removeObserver(services_->observer);
  if (registrar_)
    registrar_->runTest(static_cast<PanelRegistrar::TestMode>(111), false);
}
void SurfaceRootComponent::manageUtilPageObserver(bool enabled) {
  // Process-shared, just as the original function-local static. Single-threaded
  // application domain. Explicit wrap preserves ARM ADD/SUB without C++ UB.
  static std::int32_t activeTestCount = 0;
  const auto previous = activeTestCount;
  if (enabled) {
    activeTestCount = previous == std::numeric_limits<std::int32_t>::max()
                          ? std::numeric_limits<std::int32_t>::min()
                          : previous + 1;
    if (previous > 0)
      return;
  } else {
    activeTestCount = previous == std::numeric_limits<std::int32_t>::min()
                          ? std::numeric_limits<std::int32_t>::max()
                          : previous - 1;
    if (activeTestCount > 0)
      return;
    if (activeTestCount < 0) {
      Core::DebugPrintf("SurfaceRootComponent::manageUtilPageObserver "
                        "activeTestCount is negative!\n");
      activeTestCount = 0;
    }
  }
  if (!services_ || !services_->observer)
    throw std::logic_error("live root services and observer required");
  if (!services_->children)
    throw std::logic_error("live children required");
  auto *screen = getMainScreenComponent();
  Core::Portable::Component *component = nullptr;
  for (const auto &reference : services_->mainScreens)
    if (screen && reference.reference == screen &&
        reference.component == services_->children->findChild("mainscreen")) {
      component = reference.component;
      break;
    }
  if (!component)
    throw std::logic_error("live main screen component required");
  auto *parameter = component->getParameterByTag(2);
  if (!parameter)
    throw std::logic_error("screen tag 2 required");
  if (enabled)
    parameter->addObserver(services_->observer);
  else
    parameter->removeObserver(services_->observer);
}
} // namespace Presonus::Surface

namespace {
constexpr int kMainPage = 2;
constexpr int kMardiGrasMode = 100;
constexpr int kFirstPanelTest = 101;
constexpr int kScribbleStripMode = 105;
constexpr int kScribbleStripImage = 2002;
constexpr int kTouchscreenMode = 111;
constexpr int kTouchscreenExit = 38;
constexpr int kTouchscreenQuit = 903;
constexpr int kCalibrationTargetPage = 31;
constexpr int kCalibrateTouchPage = 32;
constexpr int kFaderUtilitiesPage = 33;
constexpr int kAudioUtilitiesPage = 34;
constexpr int kCalibrationProgress = 1000;

template <class Child>
Child *findBoundChild(const Core::Portable::Component &children,
                      const char *name, const std::vector<Child *> &bindings) {
  auto *component = children.findChild(name);
  if (!component)
    return nullptr;
  for (auto *child : bindings)
    if (component == static_cast<Core::Portable::Component *>(child))
      return child;
  return nullptr;
}

Core::Portable::Parameter &requireParameter(Core::Portable::Parameter *value) {
  if (!value)
    throw std::logic_error("live page parameter required");
  return *value;
}

float truncatedPageValue(Core::Portable::Parameter *parameter) {
  return std::trunc(requireParameter(parameter).getValue());
}
} // namespace

namespace Presonus::Surface {
MappingComponent *SurfaceRootComponent::getMappingComponent() const {
  if (!services_ || !services_->children)
    throw std::logic_error("live root component tree required");
  return findBoundChild(*services_->children, "mapping",
                        services_->mappingComponents);
}

NetworkSetupComponent *SurfaceRootComponent::getNetworkSetupComponent() const {
  if (!services_ || !services_->children)
    throw std::logic_error("live root component tree required");
  return findBoundChild(*services_->children, "networksetup",
                        services_->networkSetupComponents);
}

Core::Portable::Parameter &
SurfaceRootComponent::mainScreenParameter(int tag) const {
  if (!services_ || !services_->children)
    throw std::logic_error("live root component tree required");
  auto *screen = getMainScreenComponent();
  if (screen)
    for (const auto &binding : services_->mainScreens)
      if (binding.reference == screen &&
          binding.component == services_->children->findChild("mainscreen"))
        return requireParameter(binding.component->getParameterByTag(tag));
  throw std::logic_error("live main screen binding required");
}

Core::Portable::IParamObserver *SurfaceRootComponent::pageObserver() const {
  if (!services_ || !services_->observer)
    throw std::logic_error("live root page observer required");
  return services_->observer;
}

Core::Portable::Parameter &SurfaceRootComponent::rootParameter(int tag) const {
  if (!services_ || !services_->rootParameters)
    throw std::logic_error("live root parameters required");
  return requireParameter(services_->rootParameters->getParameterByTag(tag));
}

void SurfaceRootComponent::paramChangedScribbleStripImageTest(bool enabled) {
  if (!registrar_)
    return;
  const auto mode = static_cast<PanelRegistrar::TestMode>(kScribbleStripMode);
  if (enabled)
    registrar_->runTest(mode, true);
  rootParameter(kScribbleStripImage).setValue(enabled ? 1 : 0, false);
  manageUtilPageObserver(enabled);
  if (!enabled)
    registrar_->runTest(mode, false);
}

void SurfaceRootComponent::paramChangedLaunchTestTouchscreen(bool launch) {
  Core::DebugPrintf(
      "SurfaceRootComponent::paramChangedLaunchTestTouchscreen %s\n",
      launch ? "true" : "false");
  if (!launch)
    return;
  auto &page = mainScreenParameter(kTouchscreenExit);
  page.setValue(1, true);
  auto *observer = pageObserver();
  page.addObserver(observer);
  rootParameter(kTouchscreenQuit).addObserver(observer);
  if (registrar_)
    registrar_->runTest(static_cast<PanelRegistrar::TestMode>(kTouchscreenMode),
                        true);
  services_->touchscreenActive = true;
  rootParameter(kTouchscreenMode).setValue(0, false);
}

void SurfaceRootComponent::stopAllTests() {
  for (int tag = kFirstPanelTest; tag < kScribbleStripMode; ++tag) {
    auto &parameter = rootParameter(tag);
    if (truncatedPageValue(&parameter) != 0) {
      parameter.setValue(0, false);
      manageUtilPageObserver(false);
    }
  }
  auto &scribble = rootParameter(kScribbleStripMode);
  if (truncatedPageValue(&scribble) != 0)
    scribble.setValue(0, false);
}

void SurfaceRootComponent::paramChangedLaunchMardiGras(bool enabled) {
  if (registrar_)
    registrar_->runTest(static_cast<PanelRegistrar::TestMode>(kMardiGrasMode),
                        enabled);
  if (!enabled) {
    stopAllTests();
    return;
  }
  for (int tag = kFirstPanelTest; tag < kScribbleStripMode; ++tag) {
    auto &parameter = rootParameter(tag);
    if (parameter.getValue() == 0) {
      parameter.setValue(1, false);
      manageUtilPageObserver(true);
    }
  }
  auto &scribble = rootParameter(kScribbleStripMode);
  if (scribble.getValue() == 0)
    scribble.setValue(1, false);
}

void SurfaceRootComponent::paramChangedExitUtilPage(
    Core::Portable::Parameter *parameter) {
  if (truncatedPageValue(parameter) != 0)
    return;
  auto &mardiGras = rootParameter(kMardiGrasMode);
  if (truncatedPageValue(&mardiGras) != 0)
    mardiGras.setValue(0, false);
  stopAllTests();
  if (registrar_)
    registrar_->runTest(static_cast<PanelRegistrar::TestMode>(kMardiGrasMode),
                        false);
}

void SurfaceRootComponent::paramChangedExitAudioUtilitiesPage() {
  mainScreenParameter(kAudioUtilitiesPage).removeObserver(pageObserver());
  for (const int tag : {115, 116, 117, 118}) {
    auto &parameter = rootParameter(tag);
    if (truncatedPageValue(&parameter) > 0)
      parameter.setValue(0, false);
  }
}

void SurfaceRootComponent::paramChangedExitDiagnositcsPage(
    Core::Portable::Parameter *parameter) {
  if (truncatedPageValue(parameter) != 0)
    return;
  for (const int tag : {110, 105, 109, 108}) {
    auto &test = rootParameter(tag);
    if (truncatedPageValue(&test) > 0) {
      test.setValue(0, false);
      if (tag != kScribbleStripMode) {
        if (!registrar_)
          throw std::logic_error("live panel registrar required");
        registrar_->runTest(static_cast<PanelRegistrar::TestMode>(tag), false);
      }
    }
  }
  mainScreenParameter(kCalibrationTargetPage).removeObserver(pageObserver());
}

void SurfaceRootComponent::paramChangedLaunchAudioUtilities() {
  auto &page = mainScreenParameter(kAudioUtilitiesPage);
  page.setValue(1, true);
  page.addObserver(pageObserver());
}

void SurfaceRootComponent::paramChangedLaunchFaderUtilities(bool launch) {
  if (!launch)
    return;
  auto &page = mainScreenParameter(kFaderUtilitiesPage);
  page.setValue(1, true);
  page.addObserver(pageObserver());
  if (!registrar_)
    throw std::logic_error("live panel registrar required");
  registrar_->requestUpdatedFaderParameters();
}

void SurfaceRootComponent::paramChangedQuitTestTouchscreen() {
  if (!services_ || !services_->touchscreenActive)
    return;
  Core::DebugPrintf("SurfaceRootComponent::paramChangedQuitTestTouchscreen\n");
  terminateTestTouchscreen();
  mainScreenParameter(kMainPage).setValue(1, true);
}

void SurfaceRootComponent::paramChangedLaunchCalibrateTouchPage(bool launch) {
  const auto mode = static_cast<PanelRegistrar::TestMode>(106);
  auto *observer = pageObserver();
  if (!launch) {
    rootParameter(kCalibrationProgress).removeObserver(observer);
    mainScreenParameter(kCalibrateTouchPage).removeObserver(observer);
    return;
  }
  auto &page = mainScreenParameter(kCalibrateTouchPage);
  page.setValue(1, true);
  page.addObserver(observer);
  if (!registrar_)
    throw std::logic_error("live panel registrar required");
  registrar_->runTest(mode, true);
  requireParameter(registrar_->getParameterByTag(kCalibrationProgress))
      .addObserver(observer);
}

void SurfaceRootComponent::paramChangedExitTestTouchscreenPage(
    Core::Portable::Parameter *parameter) {
  Core::DebugPrintf(
      "SurfaceRootComponent::paramChangedExitTestTouchscreenPage\n");
  if (truncatedPageValue(parameter) == 0)
    terminateTestTouchscreen();
}

void SurfaceRootComponent::paramChangedExitFaderUtilitiesPage(
    Core::Portable::Parameter *parameter) {
  if (truncatedPageValue(parameter) == 0)
    mainScreenParameter(kFaderUtilitiesPage).removeObserver(pageObserver());
}

void SurfaceRootComponent::paramChangedExitCalibrateTouchPage(
    Core::Portable::Parameter *parameter) {
  if (truncatedPageValue(parameter) != 0)
    return;
  auto *observer = pageObserver();
  mainScreenParameter(kCalibrateTouchPage).removeObserver(observer);
  rootParameter(kCalibrationProgress).removeObserver(observer);
  if (registrar_)
    registrar_->runTest(static_cast<PanelRegistrar::TestMode>(106), false);
}

void SurfaceRootComponent::paramChangedCalibrationTarget(
    Core::Portable::Parameter *parameter) {
  if (!(truncatedPageValue(parameter) > 7))
    return;
  auto &page = mainScreenParameter(kCalibrationTargetPage);
  page.setValue(1, true);
  page.addObserver(pageObserver());
}
void SurfaceRootComponent::paramChangedDiagnositcsPage() {
  auto &page = mainScreenParameter(kCalibrationTargetPage);
  const auto *mapping = getMappingComponent();
  if (mapping && (mapping->getModifiers() & 7) == 4) {
    page.setValue(1, true);
    page.addObserver(pageObserver());
  }
}

void SurfaceRootComponent::onMainScreenParamChanged(
    Core::Portable::Parameter *parameter) {
  switch (requireParameter(parameter).getTag()) {
  case kMainPage:
    paramChangedExitUtilPage(parameter);
    break;
  case kCalibrationTargetPage:
    paramChangedExitDiagnositcsPage(parameter);
    break;
  case kCalibrateTouchPage:
    paramChangedExitCalibrateTouchPage(parameter);
    break;
  case kFaderUtilitiesPage:
    paramChangedExitFaderUtilitiesPage(parameter);
    break;
  case kAudioUtilitiesPage:
    paramChangedExitAudioUtilitiesPage();
    break;
  case kTouchscreenExit:
    paramChangedExitTestTouchscreenPage(parameter);
    break;
  }
}

void SurfaceRootComponent::storeSettings() const {
  if (!services_ || !services_->settings || !services_->rootParameters)
    throw std::logic_error("live root settings and parameter tree required");
  auto &settings = *services_->settings;
  auto &section = settings.getSection("surface");
  section.removeAll();
  Core::Portable::AttributesBuilder builder(section);
  Core::Portable::OutputStorage storage(builder);
  services_->rootParameters->save(storage);
  settings.setDirty();
}
} // namespace Presonus::Surface

namespace Presonus::Surface {
void SurfaceRootComponent::networkChanged(const Presonus::WIFIManager &) {}
void SurfaceRootComponent::screenTouched(
    const Presonus::Panel::ControlRegistrar &, int, int, int, int) {}
} // namespace Presonus::Surface
