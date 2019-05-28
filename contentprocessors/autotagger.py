from model import AmbarTaggingRule
from apiproxy import ApiProxy
from logger import AmbarLogger
from parsers.contenttypeanalyzer import ContentTypeAnalyzer
import re
import spacy

class AutoTagger:
    def __init__(self, Logger, ApiProxy):
        self.logger = Logger
        self.apiProxy = ApiProxy
        self.AUTO_TAG_TYPE = 'auto'
        self.SOURCE_TAG_TYPE = 'source'
    
    def AutoTagAmbarFile(self, AmbarFile):
        self.SetOCRTag(AmbarFile)
        self.SetSourceIdTag(AmbarFile)
        self.SetArchiveTag(AmbarFile)
        self.SetImageTag(AmbarFile)
        self.CustomTagger(AmbarFile)


        for rule in self.GetTaggingRules():
            self.ProcessTaggingRule(rule, AmbarFile)

    def ProcessTaggingRule(self, TaggingRuleToProcess, AmbarFile):
        try:
            if TaggingRuleToProcess.field == 'content':
                match = re.search(TaggingRuleToProcess.regex, AmbarFile['content']['text'])
            elif TaggingRuleToProcess.field == 'path':
                match = re.search(TaggingRuleToProcess.regex, AmbarFile['meta']['full_name'])
            else:
                self.logger.LogMessage('error', 'error applying autotagging rule {0}, no such field known {1}'.format(TaggingRuleToProcess.name, TaggingRuleToProcess.field))
                return

            if match:
                for tag in TaggingRuleToProcess.tags:
                    self.AddTagToAmbarFile(AmbarFile['file_id'], AmbarFile['meta']['full_name'], self.AUTO_TAG_TYPE, tag)
        except Exception as ex:
            self.logger.LogMessage('error', 'error applying autotagging rule {0} to {1} {2}'.format(TaggingRuleToProcess.name, AmbarFile['meta']['full_name'], str(ex)))

    def GetTaggingRules(self):
        taggingRules = []

        apiResp = self.apiProxy.GetTaggingRules()

        if not apiResp.Success: 
            self.logger.LogMessage('error', 'error retrieving autotagging rules {0}'.format(apiResp.message))
            return taggingRules
        
        if not (apiResp.Ok):
            self.logger.LogMessage('error', 'error retrieving autotagging rules, unexpected response code {0} {1}'.format(apiResp.code, apiResp.message))
            return taggingRules

        for ruleDict in apiResp.payload:
            taggingRules.append(AmbarTaggingRule.Init(ruleDict))

        return taggingRules
    
    def SetSourceIdTag(self, AmbarFile):
        self.AddTagToAmbarFile(AmbarFile['file_id'], AmbarFile['meta']['full_name'] ,self.SOURCE_TAG_TYPE, AmbarFile['meta']['source_id'])        

    def SetOCRTag(self, AmbarFile):
        if AmbarFile['content']['ocr_performed']:
            self.AddTagToAmbarFile(AmbarFile['file_id'], AmbarFile['meta']['full_name'], self.AUTO_TAG_TYPE, 'ocr_test')
            #print(AmbarFile)

    def SetArchiveTag(self, AmbarFile):
        if ContentTypeAnalyzer.IsArchive(AmbarFile['meta']['full_name']):
            self.AddTagToAmbarFile(AmbarFile['file_id'], AmbarFile['meta']['full_name'], self.AUTO_TAG_TYPE, 'archive')

    def SetImageTag(self, AmbarFile):
        if ContentTypeAnalyzer.IsImageByContentType(AmbarFile['content']['type']):
            self.AddTagToAmbarFile(AmbarFile['file_id'], AmbarFile['meta']['full_name'], self.AUTO_TAG_TYPE, 'image')

    def AddTagToAmbarFile(self, FileId, FullName, TagType, Tag):
        apiResp = self.apiProxy.AddFileTag(FileId, TagType, Tag)

        if not apiResp.Success: 
            self.logger.LogMessage('error', 'error adding {0} tag to file {1} {2}'.format(Tag, FullName, apiResp.message))
            return False
        
        if not (apiResp.Ok or apiResp.Created):
            self.logger.LogMessage('error', 'error adding {0} tag to file, unexpected response code {1} {2} {3}'.format(Tag, FullName, apiResp.code, apiResp.message))
            return False
        
        self.logger.LogMessage('verbose', '{0} tag added to {1}'.format(Tag, FullName))


    ### CUSTOM
    def CustomTagger(self, AmbarFile):
        fileString = AmbarFile['meta']['full_name']
        fileContent = AmbarFile['content']['text']
        self.logger.LogMessage('verbose', 'filePath --------------------- {0}'.format(fileString))
        #/home/aptus/labelling/test/sample.txt
        with open("home/aptus/labelling/test/"+fileString.split(".pdf")[0]+".txt", "wb+") as f: 
            f.write(fileContent) 
        
        text = fileContent
        nlp = spacy.load("en_core_web_sm")
        person = 0    
        self.logger.LogMessage('verbose', 'sentence --------------------- {0}'.format(len(text.split())))
        for sentence in text.split("."):

            self.logger.LogMessage('verbose', 'sentence --------------------- {0}'.format(sentence))
            doc = nlp(sentence)
            ents = [(e.text,e.label_) for e in doc.ents]
            for i in ents:
                self.logger.LogMessage('verbose', 'entities --------------------- {0} --- {1}'.format(i[0], i[1]))
                if i[1] == 'PERSON':
                    person = 1
                    break
            
        if(person==1):
            self.AddTagToAmbarFile(AmbarFile['file_id'], AmbarFile['meta']['full_name'], self.AUTO_TAG_TYPE, 'person')
            person = 0
        

        '''
        if('outerFolder' in fileString):
            self.logger.LogMessage('verbose', 'outerFolder is in {0}'.format(fileString))
            self.AddTagToAmbarFile(AmbarFile['file_id'], AmbarFile['meta']['full_name'], self.AUTO_TAG_TYPE, 'outerFolder')
        '''
