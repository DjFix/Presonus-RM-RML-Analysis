#pragma once
#include "core/portable/coreparams.h"
namespace Presonus {
// Three observed application slots. No virtual destructor slot is invented;
// lifetime belongs to the concrete owner. This source interface is not ARM ABI.
class IMainScreenPageController {
public:
  virtual bool connectParameter(const char *, Core::Portable::Parameter *) = 0;
  virtual void disconnectMappables() = 0;
  virtual const char *getPageName() const = 0;

protected:
  ~IMainScreenPageController() = default;
};
} // namespace Presonus
