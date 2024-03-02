#!/usr/bin/python3
import re
import nltk
import os
import sys
import getopt
import pickle
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

stemmer = PorterStemmer()

OPT = ['NOT','AND','OR']
ORDER_OPT = {'NOT':2,'AND':1,'OR':0}

def usage():
    print("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")

def run_search(dict_file, postings_file, queries_file, results_file):
    """
    using the given dictionary file and postings file,
    perform searching on the given queries file and output the results to a file
    """
    print('running search on the queries...')
    # This is an empty method
    # Pls implement your code in below
    f_dictionary = open(os.path.join(os.path.dirname(__file__),dict_file),'rb')
    dictionary = pickle.load(f_dictionary)
    name_doc_ids = 'doc_ids'
    f_doc_ids = open(os.path.join(os.path.dirname(__file__),name_doc_ids),'rb')
    doc_ids = pickle.load(f_doc_ids)
    f_queries = open(os.path.join(os.path.dirname(__file__),queries_file),'rb')
    queries = [query.decode() for query in f_queries.read().splitlines()]
    f_postings = open(os.path.join(os.path.dirname(__file__),postings_file),'rb')
    results = []
    for query in queries:
        parsed_query = parser(query)
        if parsed_query==[]:
            results.append(parsed_query)
            continue 
        term_stack = []
        for token in parsed_query:
            if token not in OPT:
                term_stack.append(token)
                continue 
            if token =='NOT':
                term1 = term_stack.pop()
                if not isinstance(term1,list):
                    term1 = get_postings(term1,dictionary,f_postings)
                term_stack.append(NOT(term1,doc_ids))
            else: 
                term1 = term_stack.pop()
                term2 = term_stack.pop()
                
                if not isinstance(term1,list):
                    term1 = get_postings(term1,dictionary,f_postings)
                if not isinstance(term2,list):
                    term2 = get_postings(term2,dictionary,f_postings)    
                if token == 'AND':
                    term_stack.append(AND(term1,term2))     
                elif token == 'OR':
                    term_stack.append(OR(term1,term2))
        
        if len(term_stack) > 1:
            print(
                "ERROR - phrasal queries not supported. Please do not give multiple isolated words without operators separating them"
            )
            term_stack = ["Error"]
        else:
            term1 = term_stack.pop()
        
            if not isinstance(term1,list):
                term1 = get_postings(term1,dictionary,f_postings)
            
            for value in term1:
                if not isinstance(value,str):
                    term_stack.append(value)
        results.append(term_stack)
        
    f_results = open(os.path.join(os.path.dirname(__file__),results_file),'w')
    for result in results:
        if len(result) == 0:
            f_results.write('\n')
        else: 
            str_res = ' '.join([str(doc_id) for doc_id in result])
            str_res = str_res.rstrip()
            f_results.write(str_res + '\n')
    f_dictionary.close()
    f_results.close()
    f_postings.close()
    f_queries.close()    


def parser(query):
    if query == '':
        return []
    
    tokens = query.rstrip().split(' ')
    processed_tokens = []
    for token in tokens:
        ed_count = 0
        cur_token = token
         
        if token[0]=='(':
            processed_tokens.append('(')
            cur_token = cur_token[1:]
        if token[-1]==')':
            ed_count+=1
            cur_token = cur_token[:-1]
        if ed_count>0:
            processed_tokens.append(cur_token)
            processed_tokens.append(')')
        else:
            processed_tokens.append(cur_token)

    # below is the code for shunting yard algorithm
    output_queue = []
    opt_stack = []
    
    while processed_tokens:
        processed_token = processed_tokens.pop(0)
        if (processed_token not in OPT) and processed_token != '(' and processed_token != ')':
            output_queue.append(stemmer.stem(processed_token.lower()))
        elif processed_token in OPT:
            while (opt_stack
                and opt_stack[-1] != "("
                and (
                    ORDER_OPT[opt_stack[-1]] > ORDER_OPT[processed_token]
                    or (
                        ORDER_OPT[opt_stack[-1]]
                        == ORDER_OPT[processed_token]
                        and processed_token != "NOT"
                    )
                )
            ):
                output_queue.append(opt_stack.pop())
            opt_stack.append(processed_token)
        elif processed_token == '(':
            opt_stack.append('(')
        elif processed_token == ')':
            try:
                while(opt_stack[-1]!='('):
                    output_queue.append(opt_stack.pop())
                if opt_stack[-1]=='(':
                    opt_stack.pop()
            except:
                print("Mismatched parenthesis detected for query '{}'".format(query))
                return []
    if not processed_tokens: 
        while opt_stack:
            opt = opt_stack.pop()
            if opt=='(':
                print("Mismatched parenthesis detected for query '{}'".format(query))
                return []
            
            output_queue.append(opt)
    return output_queue

def get_postings(term,dictionary,f_postings):
    try: 
        ptr = dictionary[term]['pointer']
        f_postings.seek(ptr,0)
        postings_list = pickle.load(f_postings)
    except:
        postings_list = []
    return postings_list

def skip_ptr_check(value):
    if isinstance(value,str):
        return int(value[1:])
    return None 

def NOT(plist1,plist2):
    result = []
    cur_idx_1 = cur_idx_2 = 0
    skip_ptr1 = skip_ptr2 = 0
    
    while True: 
        if cur_idx_2 >= len(plist2):
            return result
        elif cur_idx_1 >= len(plist1):
            for value in plist2[cur_idx_2:]:
                if skip_ptr_check(value) == None: 
                    result.append(value)
            return result
        
        cur_value_1 = plist1[cur_idx_1]
        cur_value_2 = plist2[cur_idx_2]
        
        skip_ptr1 = skip_ptr_check(cur_value_1)
        skip_ptr2 = skip_ptr_check(cur_value_2)

        
        if skip_ptr1 != None :
            cur_idx_1 += 1
            cur_value_1 = plist1[cur_idx_1]
            
        if skip_ptr2 != None: 
            cur_idx_2 += 1
            cur_value_2 = plist2[cur_idx_2]
            
        if cur_value_1 == cur_value_2:
            cur_idx_1+=1
            cur_idx_2+=1
        
        elif cur_value_2 < cur_value_1:
            result.append(cur_value_2)
            if skip_ptr2 != None:
                if skip_ptr2 == len(plist2)-1:
                    skip_value2 = plist2[skip_ptr2]
                else: 
                    skip_value2 = plist2[skip_ptr2+1]
                if skip_value2 <= cur_value_1:
                    for doc_id in plist2[cur_idx_2+1:skip_ptr2]:
                        result.append(doc_id)
                    
                    cur_idx_2 = skip_ptr2+1
                    skip_ptr2 = skip_ptr_check(plist2[skip_ptr2])
                else:
                    cur_idx_2 += 1
            else:
                cur_idx_2 += 1
        elif cur_value_2 > cur_value_1:
            if skip_ptr1 != None:
                if skip_ptr1 == len(plist1) - 1:
                    skip_value1 = plist1[skip_ptr1]
                else: 
                    skip_value1 = plist1[skip_ptr1+1]
                    
                if skip_value1 <= cur_value_2: 
                    cur_idx_1 = skip_ptr1+1
                    skip_ptr1 = skip_ptr_check(plist1[skip_ptr1])
                else: 
                    cur_idx_1 += 1
            else:
                cur_idx_1 += 1
    return result
def AND(plist1,plist2):
    result = []
    
    cur_idx1 = cur_idx2 = 0
    skip_ptr1 = skip_ptr2 = 0
    
    while True: 
        if cur_idx2 >= len(plist2) or cur_idx1>=len(plist1):
            return result
        cur_value1 = plist1[cur_idx1]
        cur_value2 = plist2[cur_idx2]
        skip_ptr1 = skip_ptr_check(cur_value1)
        skip_ptr2 = skip_ptr_check(cur_value2)
        if skip_ptr1 != None:
            cur_idx1 += 1
            cur_value1 = plist1[cur_idx1]
        if skip_ptr2 != None:
            cur_idx2 += 1
            cur_value2 = plist2[cur_idx2]
        if cur_value1 == cur_value2:
            cur_idx1 += 1
            cur_idx2 += 1
            result.append(cur_value1)
        elif cur_value2<cur_value1:
            if skip_ptr2 != None: 
                if skip_ptr2 ==len(plist2)-1:
                    skip_value2 = plist2[skip_ptr2]
                else:
                    skip_value2 = plist2[skip_ptr2+1]
                if skip_value2 <= cur_value1:
                    cur_idx2 = skip_ptr2 + 1
                    skip_ptr2 = skip_ptr_check(plist2[skip_ptr2])
                else: 
                    cur_idx2 += 1
            else: 
                cur_idx2 += 1
        else:
            if skip_ptr1 != None: 
                if skip_ptr1 == len(plist1)-1:
                    skip_value1 = plist1[skip_ptr1]
                else:
                    skip_value1 = plist1[skip_ptr1+1]
                if skip_value1 <= cur_value2:
                    cur_idx1 = skip_ptr1+1
                    skip_ptr1  = skip_ptr_check(plist1[skip_ptr1])
                else: 
                    cur_idx1 +=1
            else: 
                cur_idx1+=1
    return result

def OR(plist1,plist2):
    result = []
    cur_idx1 = cur_idx2 = 0
    skip_ptr1 = skip_ptr2 = 0
    
    while True:
        if cur_idx2>=len(plist2):
            for value in plist1[cur_idx1:]:
                if skip_ptr_check(value)==None: 
                    result.append(value)
            return result
        elif cur_idx1 >= len(plist1):
            for value in plist2[cur_idx2:]:
                if skip_ptr_check(value)==None:
                    result.append(value)
            return result
        cur_value1 = plist1[cur_idx1]
        cur_value2 = plist2[cur_idx2]
        skip_ptr1 = skip_ptr_check(cur_value1)
        skip_ptr2 = skip_ptr_check(cur_value2)
        if skip_ptr1 != None: 
            cur_idx1 += 1
            cur_value1 = plist1[cur_idx1]
        if skip_ptr2 != None: 
            cur_idx2 += 1
            cur_value2 = plist2[cur_idx2]
        
        if cur_value1==cur_value2:
            result.append(cur_value1)
            cur_idx1 += 1
            cur_idx2 += 1
        elif cur_value1 > cur_value2:
            result.append(cur_value2)
            if skip_ptr2 != None:
                if skip_ptr2 == len(plist2)-1:
                    skip_value2 = plist2[skip_ptr2]
                else:
                    skip_value2 =plist2[skip_ptr2+1]
                if skip_value2 <= cur_value1:
                    for document in plist2[cur_idx2+1 : skip_ptr2]:
                        result.append(document)
                    cur_idx2 = skip_ptr2 + 1
                    skip_ptr2 = skip_ptr_check(plist2[skip_ptr2])
                else:
                    cur_idx2 += 1
            else:
                cur_idx2 += 1
        else: 
            result.append(cur_value1)
            if skip_ptr1 != None: 
                if skip_ptr1 == len(plist1)-1:
                    skip_value1 = plist1[skip_ptr1]
                else:
                    skip_value1 = plist1[skip_ptr1+1]
                if skip_value1 <= cur_value2:
                    for document in plist1[cur_idx1+1:skip_ptr1]:
                        result.append(document)
                    cur_idx1 = skip_ptr1+1
                    skip_ptr1 = skip_ptr_check(plist1[skip_ptr1])
                else:
                    cur_idx1 += 1
            else:
                cur_idx1 += 1
    return result


                 
    
dictionary_file = postings_file = file_of_queries = output_file_of_results = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-d':
        dictionary_file  = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        file_of_output = a
    else:
        assert False, "unhandled option"

if dictionary_file == None or postings_file == None or file_of_queries == None or file_of_output == None :
    usage()
    sys.exit(2)

run_search(dictionary_file, postings_file, file_of_queries, file_of_output)

