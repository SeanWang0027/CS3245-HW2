#!/usr/bin/python3
import re
import nltk
import sys
import getopt
import os
import glob
import pickle
import math

stemmer = nltk.stem.PorterStemmer()


def usage():
    print(
        "usage: "
        + sys.argv[0]
        + " -i directory-of-documents -d dictionary-file -p postings-file"
    )

# Main function
def build_index(in_dir, out_dict, out_postings):
    """
    build index from documents stored in the input directory,
    then output the dictionary file and postings file
    """
    print("indexing...\n")
    # This is an empty method
    # Pls implement your code in below
    directory = os.path.join(os.path.dirname(__file__), "disk")
    if not os.path.exists(directory):
        os.mkdir(directory)
    for files in os.listdir(directory):
        file_path = os.path.join(directory, files)
        os.remove(file_path)
    out_postings_file = os.path.join(os.path.dirname(__file__), out_postings)
    out_dict_file = os.path.join(os.path.dirname(__file__), out_dict)
    with open(out_dict_file, "w") as f:
        print('Opening dictionary file successfully')
    with open(out_postings_file, "w") as f:
        print('Opening posting lists file successfully')
    BLOCK_SIZE = 2500000  
    totalblk = create_blk(in_dir, BLOCK_SIZE)
    CHUNK_SIZE = BLOCK_SIZE // (totalblk+1)
    SPIMI(CHUNK_SIZE, out_dict, out_postings)
    for files in os.listdir(directory):
        file_path = os.path.join(directory, files)
        os.remove(file_path)
    os.removedirs('disk')
# Main

'''
This is a function that is written to act as a tool to help the whole system to write partial block into the mutual disk.
'''
def write_partial(term_postings_dict, blk_num):
    directory_name = os.path.join(os.path.dirname(__file__), "disk")
    file_name = os.path.join(directory_name, "block_{}".format(blk_num))
    with open(file_name, "wb") as out: 
        for term in sorted(term_postings_dict.keys()):
            postings_list = sorted(term_postings_dict[term])
            term_postings = [term, postings_list]
            pickle.dump(term_postings, out)
        out.close()
    print(f"partial block {blk_num} has been written out to disk")

'''
This function divides the original text into small blocks to write into the disk (mutual one).
'''
def create_blk(in_dir, BLOCK_SIZE):
    term_postings_dict = {}
    blk_num = 1
    size_used = 0 

    doc_ids = os.listdir(in_dir)
    doc_ids = sorted([int(doc_id) for doc_id in doc_ids])
    doc_ids.sort()
    f_doc_ids = open(os.path.join(os.path.dirname(__file__), "doc_ids"), "wb")

    pickle.dump(doc_ids, f_doc_ids)

    for document in doc_ids:
        f = open(os.path.join(in_dir, str(document)), "r")
        rawtext = f.read() 
        sentences = nltk.sent_tokenize(rawtext.lower()) 

        for sentence in sentences:
            words = [stemmer.stem(w) for w in nltk.word_tokenize(sentence)]

            for word in words:
                if word not in term_postings_dict:
                    word_posting_size = sys.getsizeof(word) + sys.getsizeof(document)
                    if word_posting_size + size_used > BLOCK_SIZE:
                        write_partial(term_postings_dict, blk_num)
                        blk_num += 1
                        size_used = 0  
                        term_postings_dict.clear() 
                    term_postings_dict[word] = [document]
                    size_used += word_posting_size
                else:
                    if document not in term_postings_dict[word]:
                        docID_size = sys.getsizeof(document)
                        if docID_size + size_used > BLOCK_SIZE:
                            write_partial(term_postings_dict, blk_num)
                            blk_num += 1
                            size_used = sys.getsizeof(word) + docID_size
                            term_postings_dict.clear()
                            term_postings_dict[word] = [document]
                        else:
                            term_postings_dict[word].append(document)
                            size_used += docID_size
        f.close()
    write_partial(term_postings_dict, blk_num)  
    size_used = 0
    term_postings_dict.clear()
    
    return blk_num

'''
This function serves as a function of loading program chunk.
'''
def load_chunk(block_ID,CHUNK_SIZE,open_files,chunks):
        chunk_size_read = 0
        file_chunk = [] 
        while chunk_size_read < CHUNK_SIZE:
            try: 
                thing = pickle.load(open_files[block_ID])
                file_chunk.append(thing)
                chunk_size_read += sys.getsizeof(thing)
            except:
                break
        chunks[block_ID] = file_chunk
        if len(file_chunk) > 0:
            return True
        else:
            return False
'''
SPIMI Algorithm and merging the chunks into one single file.
'''
def SPIMI(CHUNK_SIZE, out_dict, out_postings):
    files = os.listdir(os.path.join(os.path.dirname(__file__), "disk"))
    open_files = []
    chunks = [[] for i in range(len(files))]
    for file in files:
        open_files.append(open(os.path.join(os.path.dirname(__file__), "disk", file), "rb") )
    for block_ID in range(len(open_files)):
        load_chunk(block_ID,CHUNK_SIZE,open_files,chunks)
    buffer_chunk,buffer_memory_used = [],0
    word2merge = ""
    chunk2merge = []
    plist2merge = []
    doc_freq = 0
    while True:
        for chunkID, chunk in enumerate(chunks):
            if len(chunk) == 0:
                chunk_still_has_data = load_chunk(chunkID,CHUNK_SIZE,open_files,chunks)
                if not chunk_still_has_data:
                    continue
            chunk = chunks[chunkID]
            if len(chunk) != 0:
                if word2merge == "":
                    word2merge = chunk[0][0]
                    chunk2merge.append(chunkID)
                else:
                    if chunk[0][0] < word2merge:
                        word2merge = chunk[0][0]
                        chunk2merge.clear()
                        chunk2merge.append(chunkID)
                    elif chunk[0][0] == word2merge:
                        chunk2merge.append(chunkID)
        if word2merge == "":
            break
        for chunkID in chunk2merge:
            plist2merge += chunks[chunkID].pop(0)[1]
        plist2merge = list(set(plist2merge))
        plist2merge.sort()
        doc_freq = len(plist2merge)
        skip_pointer_number = int(math.sqrt(len(plist2merge)))
        skip_pointer_interval = len(plist2merge) // skip_pointer_number
        current_skip_pointer_index = 0

        for i in range(skip_pointer_number):
            target_skip_index = 1 + current_skip_pointer_index + skip_pointer_interval
            if target_skip_index >= len(plist2merge):
                target_skip_index = len(plist2merge)
            plist2merge.insert(
                current_skip_pointer_index, "^" + str(target_skip_index)
            )
            current_skip_pointer_index = target_skip_index
        buffer_memory = (sys.getsizeof(len(plist2merge)) + sys.getsizeof(word2merge) + sys.getsizeof(plist2merge[0]) * len(plist2merge))
        if buffer_memory + buffer_memory_used > CHUNK_SIZE:
            f_dict = open(os.path.join(os.path.dirname(__file__), out_dict), "r+b")
            f_postings = open(os.path.join(os.path.dirname(__file__), out_postings), "r+b")

            dictionary = {}
            if os.stat(os.path.join(os.path.dirname(__file__), out_dict)).st_size != 0:
                dictionary = pickle.load(f_dict)

            for term_postings in buffer_chunk:
                f_postings.seek(0, 2) 
                pointer = (
                    f_postings.tell()
                )
                dictionary[term_postings["word"]] = {
                    "doc_freq": term_postings["doc_freq"],
                    "pointer": pointer,
                }
                pickle.dump(term_postings["posting_list"], f_postings)

            f_dict.seek(0, 0)
            f_dict.truncate()
            pickle.dump(dictionary, f_dict) 

            f_dict.close()
            f_postings.close()

            buffer_chunk.clear()
            buffer_memory_used = 0
        buffer_chunk.append(
            {
                "word": word2merge,
                "doc_freq": doc_freq,
                "posting_list": plist2merge,
            }
        )
        buffer_memory_used += buffer_memory
        word2merge = ""
        chunk2merge = []
        plist2merge = []
        doc_freq = 0

    print("Finished indexing")

input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], "i:d:p:")
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == "-i":  # input directory
        input_directory = a
    elif o == "-d":  # dictionary file
        output_file_dictionary = a
    elif o == "-p":  # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"

if (
    input_directory == None
    or output_file_postings == None
    or output_file_dictionary == None
):
    usage()
    sys.exit(2)

build_index(input_directory, output_file_dictionary, output_file_postings)
