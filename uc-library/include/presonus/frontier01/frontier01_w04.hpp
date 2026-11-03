#pragma once
#include "core/portable/corecomponent.h"
// Intentional partial source-port classes. The application destructor ranges
// only reset dispatch pointers and call Component destruction. Using the real
// pinned provider as a base models that cleanup; original inheritance, complete
// fields, vtable addresses and ARM32 layout are not established.
namespace Presonus {
class FaderUnitComponent : public Core::Portable::Component {
public:
  ~FaderUnitComponent();
};
class MackieControlExtender : public Core::Portable::Component {
public:
  ~MackieControlExtender();
};
class MackieControlComponent : public Core::Portable::Component {
public:
  ~MackieControlComponent();
};
namespace Surface {
class AudioUtilitiesPage : public Core::Portable::Component {
public:
  ~AudioUtilitiesPage();
};
class StartPageComponent : public Core::Portable::Component {
public:
  ~StartPageComponent();
};
class FaderUtilitiesPage : public Core::Portable::Component {
public:
  ~FaderUtilitiesPage();
};
} // namespace Surface
} // namespace Presonus
