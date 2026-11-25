#include "presonus/surface/StartPageComponent.hpp"
namespace Presonus::Surface {
namespace {
constexpr int dawModeTag = 1000;
constexpr int midiModeTag = 1001;
constexpr Core::Portable::ParamInfo modeParameters[] = {
    PARAM_ALIAS(dawModeTag, "dawmode", 0),
    PARAM_ALIAS(midiModeTag, "midimode", 0),
};
} // namespace

StartPageComponent::StartPageComponent(const char *name, const char *formName,
                                       int tag)
    : PageComponent(name, formName, tag) {
  paramList.setFeedbackNeeded(true);
  addParameters(modeParameters, ARRAY_COUNT(modeParameters));
}

StartPageComponent::~StartPageComponent() = default;
bool StartPageComponent::isDawMode() const {
  return getParameterByTag(dawModeTag)->getValue() == 1.0f;
}
bool StartPageComponent::isMidiMode() const {
  return getParameterByTag(midiModeTag)->getValue() == 1.0f;
}
} // namespace Presonus::Surface
