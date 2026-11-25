#pragma once

#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"

namespace presonus::uc {
struct ElementAccess;
}

namespace Presonus::UC {

class MetaElement;

class Element {
public:
  explicit Element(const MetaElement &metadata);
  virtual ~Element();
  Element(const Element &) = delete;
  Element &operator=(const Element &) = delete;

  bool isEmpty() const;
  const MetaElement &getMetaElement() const;
  int getIndex(const Element *child) const;
  // Transfers ownership after successful insertion. The caller retains the
  // allocation if insertion throws.
  void addChild(Element *child);
  Element *findChild(const char *name) const;

private:
  friend struct presonus::uc::ElementAccess;
  Core::CString64 name_;
  Element *parent_ = nullptr;
  const MetaElement &metadata_;
  Core::Vector<Element *> children_;
};

} // namespace Presonus::UC

namespace presonus::uc {

// Independent portable access for typed adapters.
struct ElementAccess {
  static void setName(Presonus::UC::Element &element, const char *name) {
    element.name_ = name;
  }
  static const char *name(const Presonus::UC::Element &element) {
    return element.name_.str();
  }
  static const Presonus::UC::Element *
  parent(const Presonus::UC::Element &element) {
    return element.parent_;
  }
  static int childCapacity(const Presonus::UC::Element &element) {
    return element.children_.getCapacity();
  }
};

} // namespace presonus::uc
