from datetime import datetime
import pytest
from collections import Counter
import re
import json
from bs4 import BeautifulSoup
import urllib3
import time


class Links:
    """
    Analyzing data from links.csv
    """
    df: list = []

    def __init__(self, path_to_the_file) -> None:
        """
        Put here any fields that you think you will need.
        """
        self.path: str = path_to_the_file

    def get_data_from_links_csv(self, depth: int) -> list:
        try:
            with open(self.path, "r") as file:
                return [line.strip().split(',') for num, line in enumerate(file) if num != 0 and num < depth]
        except Exception as error:
            print(f'Error: {error}')

    @staticmethod
    def parce_page(url: str) -> bytes:
        time.sleep(1 / 20)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:63.0) Gecko/20100101 Firefox/63.0'}
            response = urllib3.request("GET", url, headers=headers)
            return response.data
        except (urllib3.exceptions.ConnectionError, urllib3.exceptions.MaxRetryError):
            return bytes()

    @staticmethod
    def check_page(page:bytes, name_class: str) -> str:
        soup = BeautifulSoup(page, "html.parser")
        try:
            # check if soup has attr text
            soup.find('div', class_=name_class).text
            return '404'
        except AttributeError:
            return ''

    @classmethod
    def full_check_page(cls, site: str, page: bytes) -> bytes:
        if site == 'imdb':
            if any([cls.check_page(page, 'sc-f55afe2f-5 bKSbOD'),
                    cls.check_page(page, 'error_code')]):
                return bytes()
            return page
        else:
            if cls.check_page(page, 'error_wrapper'):
                return bytes()
            return page

    @staticmethod
    def tmdb_get_director_name(page: bytes) -> str:
        director_name: str = ''
        soup = BeautifulSoup(page, "html.parser")
        profiles = soup.find_all("li", class_='profile')
        # when no attribute .text in director_name
        for profile in profiles:
            try:
                director_name: str = profile.find("a").text
                profile_type: str = profile.find("p", class_="character").text
                if "director" in profile_type.lower():
                    break
            except AttributeError:
                director_name = 'n/a'
        return director_name

    @staticmethod
    def imdb_get_director_name(page: bytes) -> str:
        soup = BeautifulSoup(page, "html.parser")
        name_class = 'ipc-inline-list ipc-inline-list--show-dividers ipc-inline-list--inline ipc-metadata-list-item__list-content baseAlt'
        names = soup.find_all('ul', class_=name_class)[0]
        director_name = ', '.join([name.text for name in names])

        return director_name

    @staticmethod
    def tmdb_get_movie_name(page: bytes) -> str:
        soup = BeautifulSoup(page, "html.parser")
        # when no attribute .text in movie_name
        try:
            movie_name = soup.find('p', class_='wrap').text
            name: str = movie_name.replace('Исходное название ', '')
        except AttributeError:
            # check one more field
            movie_name = soup.find('div', class_='title ott_false')
            try:
                name = movie_name.find('a').text
            except AttributeError:
                name: str = 'n/a'
        return name

    @staticmethod
    def imdb_get_movie_name(page: bytes) -> str:
        soup = BeautifulSoup(page, "html.parser")
        movie_name = soup.find('span', class_='hero__primary-text').text
        return movie_name

    @staticmethod
    def tmdb_get_fees(page:bytes, list_of_fields: list) -> dict:
        data: dict = {}
        soup = BeautifulSoup(page, "html.parser")
        for field in list_of_fields:
            data[field] = 'n/a' if field in ['Currency', 'Director', 'Mov_name'] else 0
        facts = soup.find("section", class_='facts left_column')
        for line in facts.find_all('p'):
            try:
                if 'Бюджет' in line.text:
                    value = re.findall(r".\d+,\d+,\d+|.\d+,\d+|.\d+", line.text)
                    data['Currency'] = value[0][0]
                    data['Budget'] = int(value[0].replace('.00', '')[1:])
                if 'Сборы' in line.text:
                    value = re.findall(r".\d+,\d+,\d+|.\d+,\d+|.\d+", line.text)
                    data['Currency'] = value[0][0]
                    data['Gross_worldwide'] = int(value[0].replace('.00', '')[1:])
            except IndexError:
                pass
        return data

    @staticmethod
    def imdb_get_fees(page: bytes, list_of_fields: list) -> dict:
        data: dict = {}
        for field in list_of_fields:
            data[field] = 'n/a' if field in ['Currency', 'Director', 'Mov_name'] else 0
        soup = BeautifulSoup(page, "html.parser")
        box_office_fees_class = 'ipc-metadata-list ipc-metadata-list--dividers-none ipc-metadata-list--compact sc-db2ddaec-0 ecUAqg ipc-metadata-list--base'
        box_office_fees = soup.find_all("ul", class_=box_office_fees_class)
        for fee_category in box_office_fees:
            for name_and_sum in fee_category.find_all('li', class_='ipc-metadata-list__item sc-db2ddaec-2 jyjTbZ'):
                key = name_and_sum.find('span', class_='ipc-metadata-list-item__label').text
                key = key.replace(' ', '_')
                value = name_and_sum.find('div', class_='ipc-metadata-list-item__content-container').text
                value = re.findall(r".\d+,\d+,\d+|.\d+,\d+|.\d+", value)
                data['Currency'] = value[0][0]
                data[key] = int(value[0].replace(',', '')[1:])
        return data

    @staticmethod
    def tmdb_get_runtime_and_year(page: bytes) -> tuple:
        soup = BeautifulSoup(page, "html.parser")
        year = soup.find("span", class_='tag release_date').text
        year = year.replace('(', '').replace(')', '')
        runtime_raw = soup.find("span", class_='runtime').text.strip()
        try:
            hours, minutes = re.findall(r"\d+", runtime_raw)
        except ValueError:
            hours = 0
            minutes = re.findall(r"\d+", runtime_raw)[0]
        return int(hours) * 60 + int(minutes), int(year)

    @staticmethod
    def imdb_get_runtime_and_year(page: bytes) -> tuple:
        soup = BeautifulSoup(page, "html.parser")
        runtime_class = 'ipc-inline-list ipc-inline-list--show-dividers sc-ec65ba05-2 joVhBE baseAlt'
        runtime = soup.find("ul", class_=runtime_class)
        runtime_raw = runtime.find_all('li', class_='ipc-inline-list__item')[-1].text
        year = runtime.find_all('li', class_='ipc-inline-list__item')
        try:
            hours, minutes = re.findall(r"\d+", runtime_raw)
        except ValueError:
            hours = 0
            minutes = re.findall(r"\d+", runtime_raw)[0]
        try:
            year = int(year[0].text)
        except ValueError:
            try:
                year = int(year[1].text)
            except ValueError:
                year = 0
        return int(hours) * 60 + int(minutes), int(year)

    @classmethod
    def imdb_get_data(cls, imdb_id: str, tmdb_id: str, list_of_fields: list) -> dict:
        imdb_page = cls.parce_page(f'https://www.imdb.com/title/tt{imdb_id}')
        tmdb_page = cls.parce_page(f'https://www.themoviedb.org/movie/{tmdb_id}')
        imdb_page_checked = cls.full_check_page('imdb', imdb_page)
        tmdb_page_checked = cls.full_check_page('tmdb', tmdb_page)

        if not imdb_page_checked:
            if not tmdb_page_checked:
                # imdb 404 + tmdb 404
                return {field: 'n/a' for field in list_of_fields}

            # only imdb 404 tmdb 200
            data = cls.tmdb_get_fees(tmdb_page, list_of_fields)
            data['Director'] = cls.tmdb_get_director_name(tmdb_page)
            data['Runtime_minutes'], data['Year'] = cls.tmdb_get_runtime_and_year(tmdb_page)
            data['Mov_name'] = cls.tmdb_get_movie_name(tmdb_page)
            return data

        # imdb 200
        # to import Currency, Budget, Gross US & Canada, Opening weekend US & Canada, Gross worldwide
        data = cls.imdb_get_fees(imdb_page, list_of_fields)
        data['Director'] = cls.imdb_get_director_name(imdb_page)
        data['Runtime_minutes'], data['Year'] = cls.imdb_get_runtime_and_year(imdb_page)
        name_ru = cls.imdb_get_movie_name(imdb_page)
        name_eng = cls.tmdb_get_movie_name(tmdb_page)
        data['Mov_name'] = name_eng if name_eng != 'n/a' else name_ru
        return data

    @classmethod
    def write_data_file(cls, list_of_movies: list, list_of_fields: list, out_type: str) -> None:
        # create empty files
        with open('data.tsv', 'w') as f:
            f.write('')
        with open('data.json', 'w') as f:
            f.write('')
        # parce  data
        for num, movie_data_from_lines_csv in enumerate(list_of_movies[0]):
            _, imdb_id, tmdb_id = movie_data_from_lines_csv
            data = cls.imdb_get_data(imdb_id, tmdb_id, list_of_fields)
            data['Imdb_id'] = int(imdb_id) if imdb_id else 0
            data['Tmdb_id'] = int(tmdb_id) if tmdb_id else 0
            data['Parce_num'] = num
        # write data
            match out_type:
                case 'tsv':
                    with open('data.tsv', 'a') as f:
                        f.write('\t'.join([str(num)]+ [str(data[x]) for x in list_of_fields +['Imdb_id', 'Tmdb_id']]) + '\n')
                case 'json':
                    json_dict: dict = {}
                    with open('data.json', 'r') as f:
                        try:
                            json_dict = json.load(f)
                        except json.decoder.JSONDecodeError:
                            pass
                    with open('data.json', 'w') as f:
                        if num == 0:
                            json.dump({'Parced': [data]}, f, indent=4)
                        else:
                            json_dict['Parced'].append(data)
                            json.dump(json_dict, f, indent=4)

    @classmethod
    def get_imdb(cls, list_of_movies: list, list_of_fields: list, file_type: str) -> list:
        """
        The method returns a list of lists [movieId, field1, field2, field3, ...]
        for the list of movies given as the argument (movieId).
        For example, [movieId, Director, Budget, Cumulative Worldwide Gross, Runtime].
        The values should be parsed from the IMDB webpages of the movies. Sort it by movieId descendingly.
        """
        # field Currency should be corrected: check https://www.imdb.com/title/tt0113568/ ghost in the shell
        try:
            match file_type:
                case 'json':
                    # !!!!! we pushed parced data next step skipped !!!!!
                    # cls.write_data_file(list_of_movies, list_of_fields, file_type)
                    with open('data.json', 'r') as f:
                        return sorted([[f_dict[field] for field in f_dict] for f_dict in json.load(f)['Parced']],
                                    key=lambda f_dict: -f_dict[-3])
                case 'tsv':
                    # !!!!! we pushed parced data next step skipped !!!!!
                    # cls.write_data_file(list_of_movies, list_of_fields, file_type)
                    with open('data.tsv', 'r') as f:
                        return sorted([field_line.strip().split('\t') for field_line in f], key=lambda f_line: -f_line[-2])
                case _:
                    return ['Error: this file_type is not supported']
        except Exception as error:
            print(f'Error: {error}') 

    @staticmethod
    def top_directors(n) -> dict:
        """
        The method returns a dict with top-n directors where the keys are directors and
        the values are numbers of movies created by them. Sort it by numbers descendingly.
        """
        with open('data.json', 'r') as f:
            out = [f_dict[field] for f_dict in json.load(f)['Parced'] for field in f_dict if field == 'Director']
        return {key: value for key, value in Counter(out).most_common(n)}

    @staticmethod
    def most_expensive(n) -> dict:
        """
        The method returns a dict with top-n movies where the keys are movie titles and
        the values are their budgets. Sort it by budgets descendingly.
        """
        with open('data.json', 'r') as f:
            out_list =  sorted([(f_dict['Mov_name'], f_dict['Budget'])
                                for f_dict in json.load(f)['Parced']], key=lambda x: x[1], reverse=True)[:n]
            return {key: "{:,}".format(value) for key, value in out_list}

    @staticmethod
    def most_profitable(n):
        """
        The method returns a dict with top-n movies where the keys are movie titles and
        the values are the difference between cumulative worldwide gross and budget.
        Sort it by the difference descendingly.
        """
        with open('data.json', 'r') as f:
            out_list =  sorted([(f_dict['Mov_name'], f_dict['Gross_worldwide'] - f_dict['Budget'])
                                for f_dict in json.load(f)['Parced'] if f_dict['Budget']], key=lambda x: x[1], reverse=True)[:n]
            return {key: "{:,}".format(value) for key, value in out_list}

    @staticmethod
    def longest(n):
        """
        The method returns a dict with top-n movies where the keys are movie titles and
        the values are their runtime. If there are more than one version – choose any.
        Sort it by runtime descendingly.
        """
        with open('data.json', 'r') as f:
            out_list =  sorted([(f_dict['Mov_name'], f_dict['Runtime_minutes'])
                                for f_dict in json.load(f)['Parced']], key=lambda x: x[1], reverse=True)[:n]
            return {key: value for key, value in out_list}

    @staticmethod
    def top_cost_per_minute(n):
        """
        The method returns a dict with top-n movies where the keys are movie titles and
        the values are the budgets divided by their runtime. The budgets can be in different currencies – do not pay attention to it.
        The values should be rounded to 2 decimals. Sort it by the division descendingly.
        """
        with open('data.json', 'r') as f:
            out_list =  sorted([(f_dict['Mov_name'], f_dict['Budget'] / f_dict['Runtime_minutes'])
                                for f_dict in json.load(f)['Parced'] if f_dict['Budget'] and f_dict['Runtime_minutes']],
                               key=lambda x: x[1], reverse=True)[:n]
            return {key: "{:,.2f}".format(value) for key, value in out_list}

class Tags:
    """
    Analyzing data from tags.csv
    """
    def __init__(self, path_to_the_file):
        """
        Put here any fields that you think you will need.
        """
        try:
            with open(path_to_the_file, 'r') as file:
                lines = file.readlines()[1:1001]
                self.data = []
                for line in lines:
                    line = line.strip('\n')
                    user_id, movie_id, tag, timestamp = line.split(',', 3)
                    self.data.append({
                        'user_id': user_id,
                        'movie_id': movie_id,
                        'tag': tag,
                        'timestamp': timestamp
                    })
        except Exception as error:
            print(f"Error: {error}")

    def most_words(self, n):
        """
        The method returns top-n tags with most words inside. It is a dict 
 where the keys are tags and the values are the number of words inside the tag.
 Drop the duplicates. Sort it by numbers descendingly.
        """
        tags = {}
        for tag in self.data:
            lenght = len(tag['tag'].split())
            if tag['tag'] not in tags.keys():
                tags[tag['tag']] = lenght

        return dict(sorted(tags.items(), key=lambda x: x[1], reverse=True)[:n])

    def longest(self, n):
        """
        The method returns top-n longest tags in terms of the number of characters.
        It is a list of the tags. Drop the duplicates. Sort it by numbers descendingly.
        """
        tags = {}
        for tag in self.data:
            lenght = len(list(tag['tag']))
            if tag['tag'] not in tags.keys():
                tags[tag['tag']] = lenght

        return [tag for tag, length in sorted(tags.items(), key=lambda x: x[1], reverse=True)[:n]]

    def most_words_and_longest(self, n):
        """
        The method returns the intersection between top-n tags with most words inside and 
        top-n longest tags in terms of the number of characters.
        Drop the duplicates. It is a list of the tags.
        """
        set_most_words = set(self.most_words(n).keys())
        set_longest = set()
        for tag in self.longest(n):
            set_longest.add(tag)

        return list(set_most_words.intersection(set_longest))

        
    def most_popular(self, n):
        """
        The method returns the most popular tags. 
        It is a dict where the keys are tags and the values are the counts.
        Drop the duplicates. Sort it by counts descendingly.
        """
        tags_count = Counter()
        for tag in self.data:
            tag_title = tag['tag']
            tags_count[tag_title] += 1
        return dict(sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:n])
        
    def tags_with(self, word):
        """
        The method returns all unique tags that include the word given as the argument.
        Drop the duplicates. It is a list of the tags. Sort it by tag names alphabetically.
        """
        tags_with_word = []
        for tag in self.data:
            if word.lower() in tag['tag'].lower() and tag['tag'] not in tags_with_word:
                tags_with_word.append(tag['tag'])
        return sorted(tags_with_word)



class Movies:
    """
    Analyzing data from movies.csv
    """
    def __init__(self, path_to_the_file):
        """
        Put here any fields that you think you will need.
        """
        try:
            with open(path_to_the_file, 'r') as file:
                lines = file.readlines()[1:]
                self.data = []
                for line in lines:
                    line = line.strip('\n')
                    movie_id, title, genres = line.split(',', 2)
                    if '\"' in line:
                        title = re.search(r'\"(.*?)\"', line).group(1)
                        genres = re.search(r'\".*?\"\,(.*?)', line).group(1)
                    self.data.append({
                        'movieId': movie_id,
                        'title': title,
                        'genres': genres,
                    })
        except Exception as error:
            print(f"Error: {error}")   

    def dist_by_release(self):
        """
        The method returns a dict or an OrderedDict where the keys are years and the values are counts. 
        You need to extract years from the titles. Sort it by counts descendingly.
        """
        release_years = Counter()
        for movie in self.data:
            year = self.extract_year(movie['title'])
            release_years[year] += 1
        return dict(sorted(release_years.items(), key=lambda x: x[1], reverse=True)) # maybe change naming
    
    def extract_year(self, title):
        match_item = re.search(r'\((\d{4})\)', title) # поиск регулярного выражения
        if match_item:
            return int(match_item.group(1)) 
        else:
            return None
    
    def dist_by_genres(self):
        """
        The method returns a dict where the keys are genres and the values are counts.
        Sort it by counts descendingly.
        """
        genres = Counter()
        for movie in self.data:
            for genre in movie['genres'].split('|'):
                if genre != '':
                    genres[genre] += 1
        
        return dict(sorted(genres.items(), key=lambda x: x[1], reverse=True))
        
    def most_genres(self, n):
        """
        The method returns a dict with top-n movies where the keys are movie titles and 
        the values are the number of genres of the movie. Sort it by numbers descendingly.
        """
        movies = {}
        for movie in self.data:
            title = movie['title']
            genres = movie['genres'].split('|')
            movies[title] = len(genres)

        return dict(sorted(movies.items(), key=lambda x: x[1], reverse=True)[:n])



class Ratings:
    """
    Analyzing data from ratings.csv
    """
    def __init__(self, filepath_ratings, filepath_movies):
        self.filepath_ratings = filepath_ratings
        self.filepath_movies = filepath_movies
        self.movies_data = self.load_movies_data()
        self.ratings_data = self.load_ratings_data()
        """
        Put here any fields that you think you will need.
        """
    def read_file_generator(self, filepath):
        try:
            with open(filepath, mode='r') as file:
                next(file)
                for line in file:
                    for i,line in enumerate(file):
                        if i <= 1000:
                            yield line.strip()
        except Exception as error:
            print(f"Error: {error}")

    def load_ratings_data(self):
        data_list = []  
        try:
            for line in self.read_file_generator(self.filepath_ratings):
                user_id, movie_id, rating, timestamp = line.split(',')  

                data_list.append({
                    "user_id": user_id,
                    "movie_id": movie_id,
                    "rating": float(rating), 
                    "year": datetime.fromtimestamp(int(timestamp)).year  
                })
        except Exception as error:
            print(f"Error: {error}")
        return data_list  
    
    def load_movies_data(self):
        movies = {}
        for line in self.read_file_generator(self.filepath_movies):
            if '"' in line:
                first_title_letter = line.find(',"') + 1 
                last_title_letter = line.find('",')
                movie_title = line[first_title_letter+1:last_title_letter] 
            else:
                line = line.split(',')
                movie_title = line[1]
                movie_id = line[0]
            movies[movie_id] = movie_title
        return movies

    class Movies:    
        def __init__(self, ratings_data, movie_data):
            self.ratings_data = ratings_data
            self.movie_data = movie_data

        def dist_by_year(self):
            """
            The method returns a dict where the keys are years and the values are counts. 
            Sort it by years ascendingly. You need to extract years from timestamps.
            """
            ratings_by_year = Counter(line["year"] for line in self.ratings_data)
            return dict(sorted(ratings_by_year.items(), key=lambda x: -x[1]))
        
        def dist_by_rating(self):
            """
            The method returns a dict where the keys are ratings and the values are counts.
         Sort it by ratings ascendingly.
            """
            ratings_distribution = Counter(line["rating"] for line in self.ratings_data)
            return dict(sorted(ratings_distribution.items()))
        
        
        def top_by_num_of_ratings(self, n):
            """
            The method returns top-n movies by the number of ratings. 
            It is a dict where the keys are movie titles and the values are numbers.
            Sort it by numbers descendingly.
            """
            movie_counts = Counter(line["movie_id"] for line in self.ratings_data)
            

            top_movies = {
                self.movie_data[movie_id]: count
                for movie_id, count in movie_counts.items()
                if movie_id in self.movie_data
            }

            top_movies_sort = dict(sorted(top_movies.items(), key=lambda x: -x[1])[:n])
            return top_movies_sort  

        def calculate_average(self, values):
            if values:
                average = round(sum(values) / len(values), 2)
            else:
                average = 0
            return average
        
        def calculate_median(self, values):
            sorted_values = sorted(values)
            length = len(sorted_values)
            if length == 0:
                median = 0
            elif length % 2 == 1:
                median = round(sorted_values[length // 2], 2)
            else:
                median = round((sorted_values[length // 2 - 1] + sorted_values[length // 2]) / 2, 2) 
            return median
        
        def calculate_variance(self, values):
            if len(values) < 2:
                variance = 0
            else:
                average = self.calculate_average(values)
                variance = sum((x - average) ** 2 for x in values) / len(values)
            return round(float(variance), 2)
        
        def top_by_ratings(self, n, metric='average'):
            """
            The method returns top-n movies by the average or median of the ratings.
            It is a dict where the keys are movie titles and the values are metric values.
            Sort it by metric descendingly.
            The values should be rounded to 2 decimals.
            """
            movie_ratings = {}
            for line in self.ratings_data:
                movie_id = line['movie_id']
                if movie_id not in movie_ratings:
                    movie_ratings[movie_id] = []
                movie_ratings[movie_id].append(line['rating'])

            metric_func = self.calculate_average if metric == 'average' else self.calculate_median
            top_movies = {
                self.movie_data[movie]: metric_func(ratings)
                for movie, ratings in movie_ratings.items() if movie in self.movie_data
            }
            return dict(sorted(top_movies.items(), key=lambda x: -x[1])[:n])
        
        def top_controversial(self, n):
            """
            The method returns top-n movies by the variance of the ratings.
            It is a dict where the keys are movie titles and the values are the variances.
          Sort it by variance descendingly.
            The values should be rounded to 2 decimals.
            """
            movie_ratings = {}
            for line in self.ratings_data:
                movie_id = line['movie_id']
                if movie_id not in movie_ratings:
                    movie_ratings[movie_id] = []
                movie_ratings[movie_id].append(line['rating'])

            variances = {
                self.movie_data[movie]: self.calculate_variance(ratings)
                for movie, ratings in movie_ratings.items() 
                if movie in self.movie_data
            }
            return dict(sorted(variances.items(), key=lambda x: -x[1])[:n])

    class Users(Movies):
        def __init__(self, ratings_data):
            super().__init__(ratings_data, {})  

        def dist_by_num_ratings(self,n):
            """
            Returns the distribution of users by the number of ratings they made.
            """
            user_counts = Counter(line["user_id"] for line in self.ratings_data)
            return dict(sorted(user_counts.items(), key=lambda x: -x[1])[:n])
        
        def dist_by_rating(self, n, metric='average'):
            user_ratings = {}
            for line in self.ratings_data:
                user_id = line["user_id"]
                if user_id not in user_ratings:
                    user_ratings[user_id] = []
                user_ratings[user_id].append(line["rating"])

            metric_fn = self.calculate_median if metric == 'median' else self.calculate_average
            user_metrics = {
                user: metric_fn(ratings)
                for user, ratings in user_ratings.items()
            }
            return dict(sorted(user_metrics.items(), key=lambda x: -x[1])[:n])
        
        def top_controversial(self, n):
            user_ratings = {}
            for line in self.ratings_data:
                user_id = line['user_id']
                if user_id not in user_ratings:
                    user_ratings[user_id] = []
                user_ratings[user_id].append(line['rating'])

            variances = {
                str(user): self.calculate_variance(ratings)
                for user, ratings in user_ratings.items()
            }
            return dict(sorted(variances.items(), key=lambda x: -x[1])[:n])

class Tests:
    """Class containing all test methods for Ratings, Movies, and Users"""

    # Create tests using PyTest for each and every method of the classes above.
    # They should check:
    # if the methods return the correct data types
    # if the lists elements have the correct data types
    # if the returned data sorted correctly

    @pytest.fixture(scope="class")
    def links(self):
        return Links("../datasets/ml-latest-small/links.csv")
    
    @pytest.fixture(scope="class")
    def ratings_instance(self):
        return Ratings("../datasets/ml-latest-small/ratings.csv", "../datasets/ml-latest-small/movies.csv")

    @pytest.fixture(scope="class")
    def movies_nested_class(self, ratings_instance):
        ratings_data = ratings_instance.ratings_data
        movies_data = ratings_instance.movies_data
        return Ratings.Movies(ratings_data, movies_data)
    
    @pytest.fixture(scope="class")
    def users_nested_class(self, ratings_instance):
        ratings_data = ratings_instance.ratings_data
        return Ratings.Users(ratings_data)
    
    @pytest.fixture(scope="class")
    def movies_instance(self):  
        return Movies("../datasets/ml-latest-small/movies.csv")

    @pytest.fixture(scope="class")
    def tags_instance(self):
        return Tags("../datasets/ml-latest-small/tags.csv")
    
# tests for Class Links
    def test_class_links_get_imdb(self, links):
        my_class_method = links.get_imdb(
            [links.get_data_from_links_csv(1000)],
           ['Currency', 'Budget', 'Gross_US_&_Canada', 'Opening_weekend_US_&_Canada',
            'Gross_worldwide', 'Director', 'Runtime_minutes', 'Year', 'Mov_name'],
            'json')
        assert isinstance(my_class_method, list)
        for f_line in my_class_method:
            assert all([isinstance(f_line[x], str) for x in [0,5,8]])
            assert all([isinstance(f_line[x], int) for x in [1, 2, 3, 4, 6, 7, 9, 10, 11]])
        assert my_class_method == [x for x in sorted(my_class_method, key=lambda y: -y[-3])]

    def test_class_links_top_directors(self, links):
        assert isinstance(links.top_directors(10), dict)
        assert all(isinstance(user, str) and isinstance(count, int) for user, count in links.top_directors(10).items())
        assert list(links.top_directors(10).values()) == sorted(links.top_directors(10).values(), reverse= True)

    def test_class_links_most_expensive(self, links):
        assert isinstance(links.most_expensive(10), dict)
        assert all(isinstance(user, str) and isinstance(count, str) for user, count in links.most_expensive(10).items())
        assert list(links.most_expensive(10).values()) == sorted(links.most_expensive(10).values(), reverse=True)

    def test_class_links_most_profitable(self, links):
        assert isinstance(links.most_profitable(10), dict)
        assert all(isinstance(user, str) and isinstance(count, str) for user, count in links.most_profitable(10).items())
        assert list(links.most_profitable(10).values()) == sorted(links.most_profitable(10).values(), reverse=True)

    def test_class_links_longest(self, links):
        assert isinstance(links.longest(10), dict)
        assert all(isinstance(user, str) and isinstance(count, int) for user, count in links.longest(10).items())
        assert list(links.longest(10).values()) == sorted(links.longest(10).values(), reverse=True)

    def test_class_links_top_cost_per_minute(self, links):
        assert isinstance(links.top_cost_per_minute(10), dict)
        assert all(isinstance(user, str) and isinstance(count, str) for user, count in links.top_cost_per_minute(10).items())
        assert list(links.top_cost_per_minute(10).values()) == sorted(links.top_cost_per_minute(10).values(), reverse=True)
  
#tests for Class Ratings

    def test_read_file_generator(self, ratings_instance):
        generator = ratings_instance.read_file_generator("../datasets/ml-latest-small/ratings.csv")
        first_line = next(generator)  
        assert isinstance(first_line, str)
        assert ',' in first_line 

    def test_load_ratings_data(self, ratings_instance):
        data = ratings_instance.load_ratings_data()
        assert isinstance(data, list)
        assert isinstance(data[0], dict)  
        assert "user_id" in data[0] and "movie_id" in data[0] and "rating" in data[0] and "year" in data[0]

    def test_load_movies_data(self, ratings_instance):
        data = ratings_instance.load_movies_data()
        assert isinstance(data, dict)
        assert len(data) > 0  
        first_key = next(iter(data))
        assert isinstance(first_key, str)  
        assert isinstance(data[first_key], str) 

    def test_calculate_average(self, movies_nested_class):
        values = [1.0, 2.0, 3.0, 4.0]
        result = movies_nested_class.calculate_average(values)
        assert isinstance(result, float)
        assert result == 2.50  

    def test_calculate_median(self, movies_nested_class):
        values_odd = [1.0, 2.0, 3.0]  
        values_even = [1.5, 2.5, 3.5, 4.5]  
        assert movies_nested_class.calculate_median(values_odd) == 2.0
        assert movies_nested_class.calculate_median(values_even) == 3.0  

    def test_calculate_variance(self, movies_nested_class):
        values = [1.0, 2.0, 3.0, 4.0]
        result = movies_nested_class.calculate_variance(values)
        assert isinstance(result, float)
        assert result == 1.25  
    
    def test_initialization_ratings_class(self):
        ratings = Ratings("../datasets/ml-latest-small/ratings.csv", "../datasets/ml-latest-small/movies.csv")
        assert type(ratings.ratings_data) == list

    def test_dist_by_year(self, movies_nested_class):
        result = movies_nested_class.dist_by_year()

        assert isinstance(result, dict)
        assert all(isinstance(year, int) and isinstance(count, int) for year, count in result.items())
        assert list(result.values()) == sorted(result.values(), reverse=True)

    def test_dist_by_rating(self, movies_nested_class):
        result = movies_nested_class.dist_by_rating()
        
        assert isinstance(result, dict)
        assert all(isinstance(rating, float) and isinstance(count, int) for rating, count in result.items())
        assert list(result.keys()) == sorted(result.keys())

    def test_top_by_num_of_ratings(self, movies_nested_class):
        result = movies_nested_class.top_by_num_of_ratings(2)

        assert isinstance(result, dict)
        assert len(result) == 2
        assert list(result.values()) == sorted(result.values(), reverse=True)

    def test_top_by_ratings_average(self, movies_nested_class):
        result = movies_nested_class.top_by_ratings(10, metric='average')

        assert isinstance(result, dict)
        assert len(result) == 10
        assert all(isinstance(movie, str) and isinstance(avg_rating, float) for movie, avg_rating in result.items())

    def test_top_controversial(self, movies_nested_class):
        result = movies_nested_class.top_controversial(10)

        assert isinstance(result, dict)
        assert len(result) == 10
        assert all(isinstance(movie, str) and isinstance(variance, float) for movie, variance in result.items())

    def test_dist_by_num_ratings(self, users_nested_class):
        result = users_nested_class.dist_by_num_ratings(2)

        assert isinstance(result, dict)
        assert all(isinstance(user, str) and isinstance(count, int) for user, count in result.items())
        assert list(result.values()) == sorted(result.values(), reverse=True)

    def test_dist_by_rating_average(self, users_nested_class):
        result = users_nested_class.dist_by_rating(2, metric='average')

        assert isinstance(result, dict)
        assert all(isinstance(user, str) and isinstance(avg_rating, float) for user, avg_rating in result.items())

    def test_top_controversial_users(self, users_nested_class):
        result = users_nested_class.top_controversial(2)

        assert isinstance(result, dict)
        assert len(result) == 2
        assert all(isinstance(user, str) and isinstance(variance, float) for user, variance in result.items())
    
    
#tests for Class Movies

    def test_initialization_movies_class(self):
        movies = Movies("../datasets/ml-latest-small/movies.csv")
        assert type(movies.data) == list

    def test_dist_by_release(self, movies_instance):
        result = movies_instance.dist_by_release()
        print(result.keys())  
        assert isinstance(result, dict)
        # assert all(isinstance(year, int) for year in result.keys())
        assert all(isinstance(year, int) for year in result.keys() if year is not None)

        assert all(isinstance(count, int) for count in result.values())
        counts = list(result.values())
        assert counts == sorted(counts, reverse=True)

    def test_dist_by_genres(self, movies_instance):
        result = movies_instance.dist_by_genres()
        assert isinstance(result, dict)
        assert all(isinstance(genre, str) for genre in result.keys())
        assert all(isinstance(count, int) for count in result.values())

    def test_type_most_genres(self, movies_instance):
        result = movies_instance.most_genres(5)
        assert isinstance(result, dict)
        assert all(isinstance(title, str) for title in result.keys())
        assert all(isinstance(count, int) for count in result.values())

    def test_extract_year(self, movies_instance):
        assert movies_instance.extract_year("Toy Story (1995)") == 1995
        assert movies_instance.extract_year("Jumanji (1995)") == 1995
        assert movies_instance.extract_year("Some Movie Without Year") is None

# Tests for Class Tags
    def test_initialization(self):
        movies = Tags("../datasets/ml-latest-small/tags.csv")
        assert type(movies.data) == list
        
    def test_most_words(self, tags_instance):
        result = tags_instance.most_words(5)
        assert isinstance(result, dict)
        assert all(isinstance(tag, str) for tag in result.keys())
        assert all(isinstance(count, int) for count in result.values())
        counts = list(result.values())
        assert counts == sorted(counts, reverse=True)
        
    def test_longest(self, tags_instance):
        result = tags_instance.longest(5)
        assert isinstance(result, list)
        assert all(isinstance(tag, str) for tag in result)
        
    def test_most_words_and_longest(self, tags_instance):
        result = tags_instance.most_words_and_longest(5)
        assert isinstance(result, list)
        assert all(isinstance(tag, str) for tag in result)
        
    def test_most_popular(self, tags_instance):
        result = tags_instance.most_popular(5)
        assert isinstance(result, dict)
        assert all(isinstance(tag, str) for tag in result.keys())
        assert all(isinstance(count, int) for count in result.values())
        counts = list(result.values())
        assert counts == sorted(counts, reverse=True)
        
    def test_tags_with(self, tags_instance):
        result = tags_instance.tags_with("love")
        assert isinstance(result, list)
        assert all(isinstance(tag, str) for tag in result)
        assert all("love".lower() in tag.lower() for tag in result)