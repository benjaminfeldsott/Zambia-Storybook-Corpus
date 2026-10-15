require 'json'
require 'fileutils'
require 'logger'

class CorpusQuestionAnswer
  def initialize(target_directory, fix_errors: false)
    @target_directory = target_directory
    @fix_errors = fix_errors
    
    @logger = Logger.new($stdout)
    @logger.formatter = proc do |level, datetime, name, message| 
      "#{datetime.strftime('%H:%M:%S')} [#{level.ljust(5)}] #{message}\n" 
    end
  end

  def run!
    error_count = 0
    fixed_count = 0

    Dir.glob(File.join(@target_directory, "**", "*.json")).each do |file_path|
      begin
        verse_data = JSON.parse(File.read(file_path))
      rescue JSON::ParserError
        @logger.error("#{File.basename(file_path)} invalid JSON. Skipping.")
        next
      end
      
      unless verse_data['body'] && verse_data['body'].is_a?(Array)
        @logger.warn("#{File.basename(file_path)} wrong format. Skipping.")
        next
      end

      file_modified = false
      
      verse_data['body'].reverse_each do |verse_current|
        verse_id = verse_current['verse']
        verse_map = verse_current['text']
        verse_structure_is_good = true
        
        # 1. Check for completely empty verses
        if verse_map.empty? || verse_map.values.all? { |v| v.strip.empty? }
          @logger.error("#{File.basename(file_path)} Verse #{verse_id}: Completely empty.")
          print_visual_error(verse_current)
          error_count += 1
          if @fix_errors
            verse_data['body'].delete(verse_current)
            fixed_count += 1
            file_modified = true
          end
          next
        end

        # 2. Check for missing Source keys
        unless verse_map.keys.any? { |k| k.start_with?('S') }
          @logger.warn("#{File.basename(file_path)} Verse #{verse_id}: Missing Source tag.")
          verse_structure_is_good = false
          error_count += 1
          if @fix_errors
            verse_map['S1'] = "[QA_FLAG_MISSING_SOURCE]"
            fixed_count += 1
            file_modified = true
          end
        end

        # 3. Check for missing Target keys
        unless verse_map.keys.any? { |k| k.start_with?('T') }
          @logger.warn("#{File.basename(file_path)} Verse #{verse_id}: Missing Target tag.")
          verse_structure_is_good = false
          error_count += 1
          if @fix_errors
            verse_map['T1'] = "[QA_FLAG_MISSING_TARGET]"
            fixed_count += 1
            file_modified = true
          end
        end

        # 4. Check for embedded, faulty tags inside the text
        verse_map.each do |verse_tag, verse_content|
          if verse_match = verse_content.match(/\b([ST]\s*\d+\s*[:;.\-]?|[ST]\d+)\b/i)
            @logger.warn("#{File.basename(file_path)} Verse #{verse_id}: Embedded/faulty tag '#{verse_match[0]}' found inside '#{verse_tag}'.")
            verse_structure_is_good = false
            error_count += 1
          end
        end

        print_visual_error(verse_current) unless verse_structure_is_good
      end

      if @fix_errors && file_modified
        File.write(file_path, JSON.pretty_generate(verse_data))
        @logger.info("Fixed and saved: #{File.basename(file_path)}")
      end
    end

    @logger.info("Total Errors Found: #{error_count} | Errors Fixed: #{fixed_count}")
  end

  private

  def print_visual_error(verse_current)
    puts "  --------------------------------------------------"
    JSON.pretty_generate(verse_current).lines.each do |verse_line|
      puts "  | #{verse_line}"
    end
    puts "  --------------------------------------------------\n\n"
  end
end

target = "/path" 

qa_auditor = CorpusQuestionAnswer.new(target, fix_errors: false)
qa_auditor.run!