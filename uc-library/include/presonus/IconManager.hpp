#pragma once

#include "core/portable/corefilename.h"
#include "core/public/corevector.h"

namespace Presonus {
class SLChannelBase;
}

// Portable source model for the recovered channel icon methods. Original ARM
// storage, unencoded declarations and manager construction remain unresolved.
class IconManager {
public:
  class ChannelCategory {
  public:
    ChannelCategory(const Core::Portable::FileName &path, bool recurse);
    ~ChannelCategory();

    void parseIcons(const Core::Portable::FileName &path, bool recurse);
    Core::CStringBuffer<256> getIconName(int index) const;
    int getIconIndex(const char *name) const;

    const Core::Portable::FileName &name() const { return name_; }
    int iconCount() const { return icons_.count(); }
    const Core::Portable::FileName &iconFile(int index) const {
      return icons_.at(index);
    }

  private:
    friend class IconManager;

    Core::Portable::FileName name_;
    Core::Vector<Core::Portable::FileName> icons_;
  };

  // Portable setup with borrowed categories in lookup order.
  explicit IconManager(Core::ConstVector<const ChannelCategory *> categories)
      : borrowedCategories_(categories) {}

  // Portable construction supplies the icon root held in original manager
  // state.
  explicit IconManager(const Core::Portable::FileName &iconRoot)
      : iconRoot_(iconRoot) {}
  ~IconManager();
  IconManager(const IconManager &) = delete;
  IconManager &operator=(const IconManager &) = delete;

  void loadIcons();

  const ChannelCategory *getCategory(int index) const;
  const ChannelCategory *
  getCategoryForIconId(Core::CStringBuffer<256> id) const;
  void suggestChannelName(const char *id, Presonus::SLChannelBase &channel,
                          Core::CStringBuffer<256> &output) const;

private:
  int categoryCount() const;
  const ChannelCategory *categoryAt(int index) const;

  Core::ConstVector<const ChannelCategory *> borrowedCategories_{nullptr, 0};
  Core::Vector<ChannelCategory *> loadedCategories_;
  Core::Portable::FileName iconRoot_;
};
