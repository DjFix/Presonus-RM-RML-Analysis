#pragma once

#include "core/portable/coreparams.h"
#include "presonus/panel/OffscreenElement.hpp"

#include <string>

namespace Presonus::Panel {
class LCDManager;

// The source-port constructor supplies the lookup context and parameter key.
// The manager and returned Core parameters are borrowed.
class FieldElement : public OffscreenElement,
                     private Core::Portable::ParamObserverBase {
public:
  FieldElement(int x, int y, const char *parameterName);
  FieldElement(std::string parameterName, LCDManager *manager);
  ~FieldElement() override;

  bool needsToDraw() const override;
  void lookupParameters();
  // The default lookup manager borrows its delegate.
  static LCDManager &defaultLookupManager();
  const Core::CString128 &textBuffer() const { return textBuffer_; }
  Core::Portable::Parameter *getParam();
  Core::Portable::Parameter *cachedParameter() const { return parameter_; }
  void setRefreshParameter(bool refresh) { refreshParameter_ = refresh; }

private:
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;

  std::string parameterName_;
  Core::CString128 textBuffer_;
  LCDManager *manager_;
  Core::Portable::Parameter *parameter_ = nullptr;
  bool refreshParameter_ = false;
};
} // namespace Presonus::Panel
