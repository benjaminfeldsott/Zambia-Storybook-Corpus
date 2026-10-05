require 'docx'
require 'json'
require 'logger'
require 'fileutils'

class BilingualCorpusParser
  attr_reader :source, :target, :folders, :logger

  # Define the header keys for source and target text translations
  HEADER_KEYS_REGEX = [
    'Title\s*\(\s*Source\s*\)',
    'Title\s*\(\s*Target\s*\)',
    'Original\s*Author',
    'Source\s*Language',
    'Target\s*Language',
    'Translator\s*\d+'
  ].join('|')

  def initialize(source, target, folders)
    @source = source
    @target = target
    @folders = folders
    
    @logger = Logger.new($stdout)
    @logger.formatter = proc do |level, datetime, name, message| 
      "#{datetime.strftime('%H:%M:%S')} [#{level.ljust(5)}] #{message}\n" 
    end
  end

  def process_directory!
    @folders.each do |folder|
      source_directory = File.join(@source, folder)
      target_directory = File.join(@target, folder)
      
      unless Dir.exist?(source_directory)
        @logger.warn("Source directory not found: #{source_directory}")
        next
      end

      FileUtils.mkdir_p(target_directory)

      Dir.glob(File.join(source_directory, "*.docx")).each do |file_path|
        parse_and_save_document(folder, target_directory, file_path)
      end
    end
    
    @logger.info("Batch processing complete.")
  end

  private

  def parse_and_save_document(folder, target_directory, file_path)
    begin
      docx = Docx::Document.open(file_path)
      full_text = docx.paragraphs.map(&:text).join("\n")
      
      # 1. Ensure that verse alignment as a condition is met
      tag_index = full_text.index(/\b[ST]\d\s*:/i)
      
      if tag_index
        header = full_text[0...tag_index]
        body = full_text[tag_index..-1]
      else
        @logger.warn("Parsed #{File.basename(file_path)} but found 0 valid S/T tags. Check formatting.")
        return
      end

      # 2. HEADER
      header_data = {}
      header.scan(/(#{HEADER_KEYS_REGEX})\s*:\s*(.*?)(?=(?:#{HEADER_KEYS_REGEX})\s*:|\z)/mi) do |key, value|
        # Regex
        regex_key = key.gsub(/\s+/, ' ').strip
        regex_key = regex_key.split.map(&:capitalize).join(' ').gsub('(source)', '(Source)').gsub('(target)', '(Target)')
        regex_value = value.gsub(/\s+/, ' ').strip
        
        header_data[regex_key] = regex_value
      end

      # Extract
      source_key = header_data.keys.find { |k| k.match(/Title\s*\(Source\)/i) }
      target_key = header_data.keys.find { |k| k.match(/Target\s*Language/i) }
      
      title = source_key ? header_data[source_key] : File.basename(file_path, ".*")
      language = target_key ? header_data[target_key] : folder
      
      regex_source_title = title.gsub(/[^0-9a-z\- ]/i, '').gsub(/\s+/, '_')
      regex_target_language = language.gsub(/[^0-9a-z\- ]/i, '').gsub(/\s+/, '_')
      output_filename = "#{regex_source_title}_#{regex_target_language}.json"
      output_path = File.join(target_directory, output_filename)

      # 3. BODY
      document_data = {
        header: header_data,
        body: []
      }

      segments = body.scan(/([ST]\d)\s*:\s*(.*?)(?=(?:[ST]\d)\s*:|\z)/mi)
      
      verse_counter = 1
      current_verse = {}

      segments.each do |label, content|
        normal_label = label.upcase
        
        # STRICT BOUNDARY
        if normal_label == "S1" && !current_verse.empty?
          document_data[:body] << {
            verse: verse_counter,
            text: current_verse
          }
          verse_counter += 1
          current_verse = {}
        end
        
        # Regex
        regex_content = content.strip.gsub(/\s+/, ' ').sub(/\s*\d+\s*\z/, '')
        current_verse[normal_label] = regex_content
      end
      
      # Finalize
      unless current_verse.empty?
        document_data[:body] << {
          verse: verse_counter,
          text: current_verse
        }
      end

      # 4. Save JSON file
      File.write(output_path, JSON.pretty_generate(document_data))
      @logger.info("Saved: #{folder}/#{output_filename} (Header keys: #{header_data.keys.size} | Verses: #{document_data[:body].size})")

    rescue StandardError => exception
      @logger.error("Failed to process #{File.basename(file_path)} | Error: #{exception.message}")
    end
  end
end

source_base = "/Users/feldsottbenjamin/Documents/Banda Docs RESEARCH"
target_base = "/Users/feldsottbenjamin/Documents/Banda RESEARCH"
language_folders = ["Chinyanja", "Ichibemba", "Sitonga", "Silozi"]

parser = BilingualCorpusParser.new(source_base, target_base, language_folders)
parser.process_directory!