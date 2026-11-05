#pragma once

namespace Presonus::Panel {
// Partial portable source model of the observed no-op base operations.
// The original ordinary return declarations are unresolved: an ARM zero result
// cannot distinguish bool, integer or pointer. unsigned int is a portable
// observation carrier, not a recovered declaration. No original fields,
// inheritance, virtual layout, lifecycle or ARM interoperability are claimed.
class Element {
public:
  unsigned int deltaEncoder(int delta);
  unsigned int tap();
  unsigned int next();
  unsigned int getParam();
  unsigned int previous();
};
} // namespace Presonus::Panel
