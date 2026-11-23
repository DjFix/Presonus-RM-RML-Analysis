#include "presonus/panel/FieldElement.hpp"

#include "core/portable/coresingleton.h"
#include "presonus/panel/LCDManager.hpp"

#include <utility>

namespace Presonus::Panel {
namespace {
class DefaultFieldLookup
    : public Core::Portable::Singleton<DefaultFieldLookup> {
public:
  LCDManager manager{LCDManager::SourcePortConstruction{}};
};
} // namespace
} // namespace Presonus::Panel

DEFINE_SINGLETON(Presonus::Panel::DefaultFieldLookup)

namespace Presonus::Panel {
FieldElement::FieldElement(int x, int y, const char *parameterName)
    : OffscreenElement(x, y),
      parameterName_(parameterName ? parameterName : ""), textBuffer_(nullptr),
      manager_(nullptr) {
  lookupParameters();
}

FieldElement::FieldElement(std::string parameterName, LCDManager *manager)
    : OffscreenElement(0, 0), parameterName_(std::move(parameterName)),
      manager_(manager) {}

FieldElement::~FieldElement() {
  if (parameter_)
    parameter_->removeObserver(this);
}

bool FieldElement::needsToDraw() const { return Element::needsToDraw(); }

LCDManager &FieldElement::defaultLookupManager() {
  return DefaultFieldLookup::instance().manager;
}

void FieldElement::lookupParameters() {
  LCDManager &manager = manager_ ? *manager_ : defaultLookupManager();
  auto *resolved = manager.lookupElementParameter(parameterName_.c_str());
  if (resolved == parameter_)
    return;
  if (parameter_)
    parameter_->removeObserver(this);
  parameter_ = resolved;
  if (parameter_)
    parameter_->addObserver(this);
  setDirty(1);
}

Core::Portable::Parameter *FieldElement::getParam() {
  if (!parameter_ || refreshParameter_)
    lookupParameters();
  return parameter_;
}

void FieldElement::paramChanged(Core::Portable::Parameter *parameter,
                                int message) {
  if (parameter == parameter_ &&
      message == Core::Portable::Parameter::kDestroyed)
    parameter_ = nullptr;
}
} // namespace Presonus::Panel
