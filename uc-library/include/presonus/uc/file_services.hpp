#pragma once
#include "core/portable/coreattributes.h"
#include "core/public/corestream.h"
#include "core/public/corestringbuffer.h"
#include "presonus/uc/file_data_events.hpp"
#include <cstdint>

namespace presonus::uc {
struct FileServicesStateAccess;
}
namespace Presonus::UC {
// Portable source interfaces. Ordinary return declarations are unencoded;
// bool/pointer/void spellings below are candidates, not an ARM ABI claim.
class IFileRequestHandler {
public:
  virtual bool readData(FileDataEvent &) = 0;
  virtual bool writeData(const FileDataEvent &) = 0;
  virtual void finish() = 0;

protected:
  ~IFileRequestHandler() = default;
};
class FileRequestHandler : public IFileRequestHandler {
public:
  explicit FileRequestHandler(Core::IO::Stream *);
  virtual ~FileRequestHandler();
  Core::IO::Stream *getStream();
  virtual bool readData(FileDataEvent &);
  virtual bool writeData(const FileDataEvent &);
  virtual void finish();

protected:
  Core::IO::Stream *stream;
};
class FileReader : public FileRequestHandler {
public:
  FileReader(Core::IO::Stream *, unsigned int);
  ~FileReader() override;
  bool readData(FileDataEvent &) override;

private:
  unsigned int total;
  std::uint32_t position;
  friend struct presonus::uc::FileServicesStateAccess;
};
class FileWriter : public FileRequestHandler {
public:
  explicit FileWriter(Core::IO::Stream *);
  ~FileWriter() override;
  bool writeData(const FileDataEvent &) override;

private:
  bool success;
  friend struct presonus::uc::FileServicesStateAccess;
};
class FileListReader {
public:
  struct Entry {
    Core::CStringBuffer<128> name, title;
    long long size;
    bool directory;
  };
  FileListReader();
  bool fromStream(Core::IO::Stream &);
  bool getNextEntry(Entry &);

private:
  Core::Portable::Attributes attributes;
  const Core::Portable::AttributeQueue *files;
  std::int32_t index;
  friend struct presonus::uc::FileServicesStateAccess;
};
class FileListWriter {
public:
  FileListWriter();
  void addEntry(const char *, const char *, long long, bool);
  void toStream(Core::IO::Stream &) const;

private:
  Core::Portable::Attributes attributes;
  Core::Portable::AttributeQueue *files;
};
} // namespace Presonus::UC
