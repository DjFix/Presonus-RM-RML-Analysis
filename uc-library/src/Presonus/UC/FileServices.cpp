#include "core/portable/corepersistence.h"
#include "presonus/uc/file_services.hpp"

namespace Presonus::UC {
FileRequestHandler::FileRequestHandler(Core::IO::Stream *value)
    : stream(value) {}
FileRequestHandler::~FileRequestHandler() { delete stream; }
Core::IO::Stream *FileRequestHandler::getStream() { return stream; }
bool FileRequestHandler::readData(FileDataEvent &) { return false; }
bool FileRequestHandler::writeData(const FileDataEvent &) { return false; }
void FileRequestHandler::finish() { delete this; }

FileReader::FileReader(Core::IO::Stream *value, unsigned int length)
    : FileRequestHandler(value), total(length), position(0) {}
FileReader::~FileReader() = default;
bool FileReader::readData(FileDataEvent &event) {
  event.wordBits[0] = position;
  event.wordBits[1] = total;
  const int count = stream->readBytes(event.data.data(), 4096);
  if (count < 0) {
    event.partBits = 2;
    return true;
  }
  event.count = static_cast<unsigned short>(count);
  position += static_cast<std::uint32_t>(count);
  event.partBits = count == 0 || (total != 0 && position >= total) ? 0 : 1;
  return true;
}

FileWriter::FileWriter(Core::IO::Stream *value)
    : FileRequestHandler(value), success(false) {}
FileWriter::~FileWriter() = default;
bool FileWriter::writeData(const FileDataEvent &event) {
  if (event.partBits > 1)
    return true;
  success = true;
  const int count = stream->writeBytes(event.data.data(), event.count);
  if (count < 0) {
    success = false;
    return false;
  }
  return true;
}

FileListReader::FileListReader()
    : attributes(Core::Portable::AttributeAllocator::getDefault()),
      files(nullptr), index(0) {}
bool FileListReader::fromStream(Core::IO::Stream &stream) {
  Core::Portable::Archiver archive(&stream, Core::Portable::Archiver::kJSON, 0);
  const bool result = archive.load(attributes);
  files = attributes.getQueue("files");
  return result;
}
bool FileListReader::getNextEntry(Entry &entry) {
  if (!files || index < 0 || index >= files->getValues().count())
    return false;
  const auto *value = files->getValues().at(index);
  if (!value)
    return false;
  const auto *attributes = value->getAttributes();
  if (!attributes)
    return false;
  entry.name = attributes->getString("name");
  entry.title = attributes->getString("title");
  entry.size = attributes->getInt("size");
  entry.directory = attributes->getInt("dir") != 0;
  ++index;
  return true;
}

FileListWriter::FileListWriter()
    : attributes(Core::Portable::AttributeAllocator::getDefault()),
      files(attributes.makeQueue("files")) {}
void FileListWriter::addEntry(const char *name, const char *title,
                              long long size, bool directory) {
  auto *entryAttributes = files->appendAttributes(attributes.getAllocator());
  entryAttributes->set("name", name, false);
  if (title && *title)
    entryAttributes->set("title", title, false);
  if (size != 0)
    entryAttributes->set("size", static_cast<Core::int64>(size));
  if (directory)
    entryAttributes->set("dir", static_cast<Core::int64>(1));
}
void FileListWriter::toStream(Core::IO::Stream &stream) const {
  Core::Portable::Archiver archive(&stream, Core::Portable::Archiver::kJSON, 1);
  archive.save(attributes);
  stream.setPosition(0, 0);
}
} // namespace Presonus::UC
