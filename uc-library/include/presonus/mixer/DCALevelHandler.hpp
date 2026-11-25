#pragma once

#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"

namespace Presonus::Mixer {

class FilterGroupComponent;

// Portable CCL source port. The handler borrows its parameters and registers
// itself on level, so the parameters must outlive it.
class DCALevelHandler : public Core::Portable::Component {
public:
  DCALevelHandler(Core::Portable::Parameter *level,
                  Core::Portable::Parameter *trim, int tag);
  ~DCALevelHandler() override;

  DCALevelHandler(const DCALevelHandler &) = delete;
  DCALevelHandler &operator=(const DCALevelHandler &) = delete;

  void addDCAMaster(FilterGroupComponent *group);
  void removeDCAMaster(FilterGroupComponent *group);
  void onDCAChange(bool respectLinkableFlag);
  void onLevelChange();
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;

private:
  float getDBValue(Core::Portable::Parameter *parameter);
  void setDBValue(Core::Portable::Parameter *parameter, float db);

  Core::Portable::Parameter *level_;
  Core::Portable::Parameter *trim_;
  Core::Vector<Core::Portable::Parameter *> masters_;
  int tag_;
  bool busy_ = false;
};

} // namespace Presonus::Mixer
