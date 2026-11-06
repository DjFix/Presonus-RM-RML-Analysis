#pragma once
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
#include "core/public/gui/corecolor.h"
#include <cstring>

namespace presonus::mapping {
class ItemOperations;
struct Entry;
class ExtendedOperations;
class ColorOperations;
} // namespace presonus::mapping

namespace Presonus {
class IMainScreenPageController;
namespace Panel {
class Control;
}
// Intentional portable source contract. Members/constructor and return types
// below do not establish the firmware declaration, layout, or ARM32 ABI.
class MappingTable {
public:
  // Initialized source-port record. Borrowed provider lifetimes exceed the
  // item. A null alias is a valid native state. This models observed roles,
  // not original fields or ARM object layout.
  class Item {
  public:
    explicit Item(Core::Portable::AliasParam *alias = nullptr,
                  Panel::Control *control = nullptr)
        : alias(alias), control(control) {}
    Item(Core::Portable::AliasParam &alias, Panel::Control *control = nullptr)
        : Item(&alias, control) {}
    static int translateMode(const char *);
    Core::Portable::AliasParam *alias;
    Panel::Control *control;
  };
  MappingTable(const presonus::mapping::Entry *sortedEntries, int count,
               presonus::mapping::ItemOperations &operations);
  Item *findItem(const char *name) const;
  Core::Portable::Parameter *getHardwareParameter(const char *name) const;
  void setControlFullOff(const char *name);
  void setControlInverseMode(const char *name, bool state);
  void setControlEnabled(const char *name, bool state);
  void setControlImmediate(const char *name, bool state);

  void connect(const char *, Core::Portable::Parameter *, const char *, bool);
  // Independent opt-in for concrete page objects; legacy borrowed gateways stay
  // in their existing domain. Set before installing pages for the new domain.
  void useTypedPageControllers() { typedPageControllers_ = true; }
  void setExtendedOperations(presonus::mapping::ExtendedOperations &);
  static void setColorOperations(presonus::mapping::ColorOperations &);
  void setControlBlinkMode(const char *, const char *);
  static int mapColor(const Core::Color &);
  static Core::Color mapColor(const char *);
  void addMainScreenPage(IMainScreenPageController *);
  // Independent source-port state observation, not an original ELF interface.
  int sourcePortPageCount() const { return pageCount_; }
  IMainScreenPageController *findPage(const char *) const;
  void setPanelControl(const char *, Panel::Control *, const char *);
  void connectAltParameter(const char *, Core::Portable::Parameter *);
  void connectTertiaryParameter(const char *, Core::Portable::Parameter *);
  void setControlColor(const char *, const char *);
  void setControlDefaultColor(const char *, const char *, bool);

private:
  presonus::mapping::ExtendedOperations &extended() const;
  bool typedPageControllers_ = false;
  presonus::mapping::ExtendedOperations *extended_ = nullptr;
  IMainScreenPageController *pages_[128]{};
  int pageCount_ = 0;
  const presonus::mapping::Entry *entries_;
  int count_;
  presonus::mapping::ItemOperations &operations_;
};
} // namespace Presonus

namespace presonus::mapping {
// Independent source-port record, not the original MappingTable::Item layout.
// Caller owns records, NUL-terminated names and opaque items for table
// lifetime. Input names must be nonnull, unique, lexically sorted and at most
// 31 bytes.
struct Entry {
  const char *name;
  Presonus::MappingTable::Item *item;
  bool operator==(const Entry &other) const {
    return std::strcmp(name, other.name) == 0;
  }
  bool operator>(const Entry &other) const {
    return std::strcmp(name, other.name) > 0;
  }
};
// Required application dependency boundary, deliberately no default/no-op
// provider. Original Item and panel behavior remain unresolved dependencies.
class ItemOperations {
public:
  virtual ~ItemOperations() = default;
  virtual void fullOff(Presonus::MappingTable::Item &) = 0;
  virtual void inverseMode(Presonus::MappingTable::Item &, bool) = 0;
  virtual void enabled(Presonus::MappingTable::Item &, bool) = 0;
  virtual void immediate(Presonus::MappingTable::Item &, bool) = 0;
};
} // namespace presonus::mapping

namespace presonus::mapping {
// Required independent application boundaries, not recovered object layouts.
// No default implementation; callers explicitly supply all dependencies.
class ColorOperations {
public:
  virtual ~ColorOperations() = default;
  virtual int map(Core::Color) = 0;
  virtual Core::Color map(const char *) = 0;
  virtual int enumFromString(const char *, int) = 0;
};
class ExtendedOperations {
public:
  virtual ~ExtendedOperations() = default;
  virtual void blink(Presonus::MappingTable::Item &, const char *) = 0;
  virtual const char *pageName(Presonus::IMainScreenPageController &) = 0;
  virtual Presonus::Panel::Control *control(Presonus::MappingTable::Item &) = 0;
  virtual void control(Presonus::MappingTable::Item &,
                       Presonus::Panel::Control *) = 0;
  virtual Core::Portable::Parameter *
  parameter(Presonus::MappingTable::Item &) = 0;
  virtual int translateMode(const char *) = 0;
  virtual void bind(Presonus::Panel::Control &, Core::Portable::Parameter *,
                    int) = 0;
  virtual Core::Portable::Parameter *alternate(Presonus::Panel::Control &,
                                               bool tertiary) = 0;
  virtual void alternate(Presonus::Panel::Control &,
                         Core::Portable::Parameter *, bool tertiary) = 0;
  virtual bool hasLED(Presonus::Panel::Control &) = 0;
  virtual void color(Presonus::Panel::Control &, int) = 0;
  virtual const char *defaultColor(Presonus::MappingTable::Item &) = 0;
  virtual void defaultColor(Presonus::MappingTable::Item &, const char *) = 0;
};
} // namespace presonus::mapping
